from odoo import api, fields, models
import logging
from odoo.exceptions import UserError
import requests
import json
from zeep import Client
from zeep.transports import Transport
_logger = logging.getLogger(__name__)

class CancelarFactura(models.TransientModel):#No almacena datos en la base de datos
	_name= "cancelar.factura.wizard"	
	_description= "Cancelacion de facturas"


	motivo = fields.Selection([
		("01", "01 - Comprobantes emitidos con errores con relación"),
		("02", "02 - Comprobantes emitidos con errores sin relación"),
		("03", "03 - No se llevó a cabo la operación"),
		("04", "04 - Operación nominativa relacionada en una factura global")
	], required=True, default="01")
	folio_fiscal_cfdi= fields.Char(string="Nuevo CFDI") #uuid_relacionado
	is_motivo_01 =fields.Boolean(string="el motivo es 01", default=False)


	@api.onchange('motivo')
	def get_user_areas(self): #Recolecta informacion de las areas asignadas al usuario actual (cada vez que se cambia al usuario)
		if self.motivo == "01": #Si el motivo es el codigo 01
			self.is_motivo_01=False 	#Se selecciono el motivo 01
		else:
			self.is_motivo_01=True

	def cancelar_factura_def(self):
		if self.motivo != "01":
			self.folio_fiscal_cfdi=""
		else:
			if(len(self.folio_fiscal_cfdi) != 36):
				raise UserError('Longitud del CFDI incorrecto, favor de revisarlo')

		factu_id = self.env.context.get('fact_id') #Id pasado por contexto desde la accion
		factura_id = self.env['account.move'].browse(factu_id) #Objeto de la factura
		factura_id.update({
			'uuid_relacionado': self.folio_fiscal_cfdi,
			'motivo_cancelacion': self.motivo
			})

		res = factura_id.with_context(active_id=factura_id.id).restricted_button_cancel_posted_moves()
		
		return res
		


class CancelarFacturaHeredado(models.Model):#No almacena datos en la base de datos
	_inherit = "account.move"

	uuid_relacionado = fields.Char(string="uuid relacionado") #related='relacion_cancelar_factura_wizard.folio_fiscal_cfdi'
	motivo_cancelacion = fields.Selection([
		("01", "01 - Comprobantes emitidos con errores con relación"),
		("02", "02 - Comprobantes emitidos con errores sin relación"),
		("03", "03 - No se llevó a cabo la operación"),
		("04", "04 - Operación nominativa relacionada en una factura global")
	], string="Motivo de cancelacion")



class AccountEdiFormatCFDI40(models.Model): #Moficaciones pasarela de tekiu y valores del XML para facturas
    _inherit = 'account.edi.format'

    #Incorporacion de los campos de motivo de cancelacion y UUID relacionado
    def _l10n_mx_edi_tekniu_cancel_invoice(self, invoice, credentials, cfdi):
        return self._l10n_mx_edi_tekniu_cancel(invoice, credentials, cfdi, False)

    def _l10n_mx_edi_tekniu_cancel_payment(self, move, credentials, cfdi):
        return self._l10n_mx_edi_tekniu_cancel(move, credentials, cfdi, True)

    def _l10n_mx_edi_tekniu_cancel(self, move, credentials, cfdi, cancel_payment):
        return self._l10n_mx_edi_tekniu_cancel_service(move, move.l10n_mx_edi_cfdi_uuid, move.company_id, credentials, cancel_payment)

    def _l10n_mx_edi_tekniu_cancel_service(self,move, uuid,company_id,credentials, cancel_payment):
        """CANCEL for Tekniu."""

        if cancel_payment:  #Cancelacion de pagos
            motivo_cancelacion = move.payment_id.motivo_cancelacion
            uuid_relacionado =  move.payment_id.uuid_relacionado
        else:               #Cancelacion de facturas
            motivo_cancelacion = move.motivo_cancelacion
            uuid_relacionado =  move.uuid_relacionado

        url = credentials['cancel_url']
        json_invoice = {
            'Cliente': {'Usuario': credentials['username'], 'Password': credentials['password']},
            'Service': 'Cancelar',
            'Prueba': credentials['test'],
            'rfc': company_id.partner_id.l10n_mx_edi_get_customer_rfc(),
            'Uuid': uuid,
            'Pass_pfx': '',
            'pfx_b64': '',
            'generate_pfx': True,
            'motivo_cancelacion': motivo_cancelacion,
            'folio': uuid_relacionado,
        }
        _logger.critical("|===================>json_invoice: %s"%json_invoice)
        
        try:
            response = requests.post(url,auth=None, verify=False, data=json.dumps({'params':json_invoice}),headers={"Content-type": "application/json"})
        except Exception as e:
            return {'errors': [str(e)]}
        result = response.json().get('result',{})
        validate = result.get('validate',False)
        code = result.get('code','')
        msg = result.get('description','')
        errors = []
        if not validate:
            errors.append(_("Code : %s") % code)
            errors.append(_("Message : %s") % msg)
            return {'errors': errors}
        return {'success': True}


	#Modificaciones cancelacion 4.0 solucionfactible
    def _l10n_mx_edi_solfact_cancel(self, move, credentials, cfdi):
        uuids = ["%s|%s|%s"%(move.l10n_mx_edi_cfdi_uuid, move.motivo_cancelacion, move.uuid_relacionado)]   ####
        return self._l10n_mx_edi_solfact_cancel_service(uuids, move.company_id, credentials)

    def _l10n_mx_edi_solfact_cancel_service(self, uuid, company, credentials):
        ''' calls the Solucion Factible web service to cancel the document based on the UUID.
        Method does not depend on a recordset
        '''
        uuids = uuid                                                                                        ####
        _logger.critical("|================>uuids%s"%uuids)                                                  ####
        certificates = company.l10n_mx_edi_certificate_ids
        certificate = certificates.sudo().get_valid_certificate()
        cer_pem = certificate.get_pem_cer(certificate.content)
        key_pem = certificate.get_pem_key(certificate.key, certificate.password)
        key_password = certificate.password

        try:
            transport = Transport(timeout=20)
            client = Client(credentials['url'], transport=transport)
            response = client.service.cancelar(
                credentials['username'], credentials['password'], uuids, cer_pem, key_pem, key_password)
        except Exception as e:
            return {
                'errors': [_("The Solucion Factible service failed to cancel with the following error: %s", str(e))],
            }

        if (response.status not in (200, 201)):
            # ws-timbrado-cancelar - status 200 : El proceso de cancelación se ha completado correctamente.
            # ws-timbrado-cancelar - status 201 : El folio se ha cancelado con éxito.
            return {
                'errors': [_("The Solucion Factible service failed to cancel with the following error: %s", response.mensaje)],
            }

        res = response.resultados
        code = getattr(res[0], 'statusUUID', None) if res else getattr(response, 'status', None)
        cancelled = code in ('201', '202')  # cancelled or previously cancelled
        # no show code and response message if cancel was success
        msg = '' if cancelled else getattr(res[0] if res else response, 'mensaje', None)
        code = '' if cancelled else code

        errors = []
        if code:
            errors.append(_("Code : %s") % code)
        if msg:
            errors.append(_("Message : %s") % msg)
        if errors:
            return {'errors': errors}

        return {'success': True}