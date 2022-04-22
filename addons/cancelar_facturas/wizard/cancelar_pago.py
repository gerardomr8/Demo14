from odoo import api, fields, models
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class CancelarPago(models.TransientModel):#No almacena datos en la base de datos
	_name= "cancelar.pago.wizard"	
	_description= "Complementos de pagos"


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

	def cancelar_pago_def(self):
		if self.motivo != "01":
			self.folio_fiscal_cfdi=""
		else:
			if(len(self.folio_fiscal_cfdi) != 36):
				raise UserError('Longitud del CFDI incorrecto, favor de revisarlo')

		pag_id = self.env.context.get('pago_id') #Id pasado por contexto desde la accion
		pago_id = self.env['account.payment'].browse(pag_id) #Objeto del pago
		pago_id.update({
			'uuid_relacionado': self.folio_fiscal_cfdi,
			'motivo_cancelacion': self.motivo
			})

		res = pago_id.with_context(active_id=pago_id.id).action_cancel()
		return res


class CancelarPagoHeredado(models.Model):
	_inherit = "account.payment"

	uuid_relacionado = fields.Char(string="uuid relacionado") #
	motivo_cancelacion = fields.Selection([
		("01", "01 - Comprobantes emitidos con errores con relación"),
		("02", "02 - Comprobantes emitidos con errores sin relación"),
		("03", "03 - No se llevó a cabo la operación"),
		("04", "04 - Operación nominativa relacionada en una factura global")
	], string="Motivo de cancelacion")