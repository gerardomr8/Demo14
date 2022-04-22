from odoo import models, fields, modules, api,tools, _
from datetime import datetime, timedelta
from lxml import etree
import logging
_log = logging.getLogger(__name__)

def _get_current_date():
    mounth_cfdi = datetime.now().month
    return int(mounth_cfdi)

def _get_current_year():
    year_cfdi = datetime.now().year
    return int(year_cfdi)


class AccountMoveCFFI40(models.Model):
    _inherit = 'account.move'

    version_cfdi = fields.Selection(
        [('3.3', 'CFDI 3.3'),
         ('4.0', 'CFDI 4.0')], string = 'Versión de timbrado', default = '4.0',
         help = 'Parametro para definir el tipo de timbrado')

    exportacion_cfdi = fields.Selection(
        [('01',	'No aplica'),
         ('02',	'Definitiva'),
         ('03',	'Temporal')], string = "Es una exportación", default = '01', 
         help = 'Atributo requerido para expresar si el comprobante ampara una operación de exportación.')

    periodicidad_cfdi = fields.Selection(
        [('01',	'Diario'),
         ('02',	'Semanal'),
         ('03',	'Quincenal'),
         ('04',	'Mensual'),
         ('05',	'Bimestral')], string = 'Periodicidad', compute = 'define_periodicity',
         help = 'Campo requerido para registrar el período al que corresponde la información del comprobante global.')
    
    states_meses =  [
        ('01',	'Enero'),
        ('02',	'Febrero'),
        ('03',	'Marzo'),
        ('04',	'Abril'),
        ('05',	'Mayo'),
        ('06',	'Junio'),
        ('07',	'Julio'),
        ('08',	'Agosto'),
        ('09',	'Septiembre'),
        ('10',	'Octubre'),
        ('11',	'Noviembre'),
        ('12',	'Diciembre'),
        ('13',	'Enero-Febrero'),
        ('14',	'Marzo-Abril'),
        ('15',	'Mayo-Junio'),
        ('16',	'Julio-Agosto'),
        ('17',	'Septiembre-Octubre'),
        ('18',	'Noviembre-Diciembre')]

    meses_cfdi = fields.Selection(
       states_meses, string = 'Meses', default = states_meses[_get_current_date()-1][0], 
        help = 'Se debe registrar la clave del mes o los meses al que corresponde la información de las operaciones celebradas con el público en general') 
    year_cfdi = fields.Integer(string = 'Año', default = _get_current_year(),
        help = 'Atributo requerido para expresar el año al que corresponde la información del comprobante global')

    tipo_relacion_cfdi = fields.Selection(
        [('01',	'Nota de crédito de los documentos relacionados'),
         ('02',	'Nota de débito de los documentos relacionados'),
         ('03',	'Devolución de mercancía sobre facturas o traslados previos'),
         ('04',	'Sustitución de los CFDI previos'),
         ('05',	'Traslados de mercancías facturados previamente'),
         ('06',	'Factura generada por los traslados previos'),
         ('07',	'CFDI por aplicación de anticipo')], string = 'CFDI origen', default = '04',
         help = 'La relación que existe entre éste comprobante (factura global) que se está generando y el o los CFDI previos que tienen alguna relación entre si.')

    uso_cfdi = fields.Selection([
        ('G01',	'Adquisición de mercancías.'),
        ('G02',	'Devoluciones, descuentos o bonificaciones.'),
        ('G03',	'Gastos en general.'),
        ('I01',	'Construcciones.'),
        ('I02',	'Mobiliario y equipo de oficina por inversiones.'),
        ('I03',	'Equipo de transporte.'),
        ('I04',	'Equipo de computo y accesorios.'),
        ('I05',	'Dados, troqueles, moldes, matrices y herramental.'),
        ('I06',	'Comunicaciones telefónicas.'),
        ('I07',	'Comunicaciones satelitales.'),
        ('I08',	'Otra maquinaria y equipo.'),
        ('D01',	'Honorarios médicos, dentales y gastos hospitalarios.'),
        ('D02',	'Gastos médicos por incapacidad o discapacidad.'),
        ('D03',	'Gastos funerales.'),
        ('D04',	'Donativos.'),
        ('D05',	'Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación).'),
        ('D06',	'Aportaciones voluntarias al SAR.'),
        ('D07',	'Primas por seguros de gastos médicos.'),
        ('D08',	'Gastos de transportación escolar obligatoria.'),
        ('D09',	'Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones.'),
        ('D10',	'Pagos por servicios educativos (colegiaturas).'),
        ('S01',	'Sin efectos fiscales.  '),
        ('CP01',	'Pagos'),
        ('CN01',	'Nómina')], string = 'Uso de CFDI', help = 'Atributo requerido para expresar la clave del uso que dará a esta factura el receptor del CFDI', default = 'G03')
    

    obj_impuesto = fields.Selection([
        ('01',	'No objeto de impuesto.'),
        ('02',	'Sí objeto de impuesto.'),
        ('03',	'Sí objeto del impuesto y no obligado al desglose.')], string = 'Es objeto de impuesto:', 
        help = 'Atributo requerido para expresar si la operación comercial es objeto o no de impuesto')
        
    def define_periodicity(self):
        customer = self.partner_id if self.partner_id.type == 'invoice' else self.partner_id.commercial_partner_id
        periocidad = customer.periodicidad_cfdi
        self.write({'periodicidad_cfdi': periocidad})

    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        res = super()._l10n_mx_edi_decode_cfdi(cfdi_data)
        if len(res.keys()) > 0:
            _log.critical(res['cadena'])
            def get_cadena(cfdi_node, template):
                if cfdi_node is None:
                    return None
                cadena_root = etree.parse(tools.file_open(template))
                return str(etree.XSLT(cadena_root)(cfdi_node))

            CFDI_XSLT_CADENA = 'cfdi_tekniu_40/data/cadenaoriginal.xslt'
            cfdi_node = res['cfdi_node']
            res['cadena'] = get_cadena(cfdi_node, CFDI_XSLT_CADENA) 
            _log.critical('GENERACION DE CADENA')
            _log.critical(res['cadena'])
        
        return res

    

    # def _get_l10n_mx_edi_signed_edi_document(self):
        # if self.version_cfdi == '3.3':
            # return super._get_l10n_mx_edi_signed_edi_document()
        # if self.version_cfdi == '4.0':
            # self.ensure_one()
            # cfdi_4_0_edi = self.env.ref('cfdi_tekniu_40.edi_cfdi_4_0')
            # return self.edi_document_ids.filtered(lambda document: document.edi_format_id == cfdi_4_0_edi and document.attachment_id)


    def test(self):
        customer = self.partner_id if self.partner_id.type == 'invoice' else self.partner_id.commercial_partner_id
        supplier = self.company_id.partner_id.commercial_partner_id
        _log.critical(customer.zip)
        _log.critical(customer.receptor_mx_edi_fiscal_regime_40)
        _log.critical(self.exportacion_cfdi)
        _log.critical(self.periodicidad_cfdi)
        _log.critical(self.meses_cfdi)
        _log.critical(self.year_cfdi)
        _log.critical(self.tipo_relacion_cfdi)
        _log.critical(self.version_cfdi)


    


        
