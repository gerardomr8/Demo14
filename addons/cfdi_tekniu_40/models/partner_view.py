# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartnerCFDI40(models.Model):
    _inherit = 'res.partner'


    receptor_mx_edi_fiscal_regime_40 = fields.Selection(
        [('601',	'General de Ley Personas Morales'),
         ('603',	'Personas Morales con Fines no Lucrativos'),
         ('605',	'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
         ('606',	'Arrendamiento'),
         ('607',	'Régimen de Enajenación o Adquisición de Bienes'),
         ('608',	'Demás ingresos'),
         ('610',	'Residentes en el Extranjero sin Establecimiento Permanente en México'),
         ('611',	'Ingresos por Dividendos (socios y accionistas)'),
         ('612',	'Personas Físicas con Actividades Empresariales y Profesionales'),
         ('614',	'Ingresos por intereses'),
         ('615',	'Régimen de los ingresos por obtención de premios'),
         ('616',	'Sin obligaciones fiscales'),
         ('620',	'Sociedades Cooperativas de Producción que optan por diferir sus ingresos'),
         ('621',	'Incorporación Fiscal'),
         ('622',	'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
         ('623',	'Opcional para Grupos de Sociedades'),
         ('624',	'Coordinados'),
         ('625',	'Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas'),
         ('626',	'Régimen Simplificado de Confianza')],string = "Régimen fiscal",
             help = "Especificar la clave vigente del régimen fiscal del contribuyente emisor bajo el cual se está emitiendo el comprobante.", default = '601')



    periodicidad_cfdi = fields.Selection(
        [('01',	'Diario'),
         ('02',	'Semanal'),
         ('03',	'Quincenal'),
         ('04',	'Mensual'),
         ('05',	'Bimestral')], string = 'Periodicidad', default = '02',
         help = 'Campo requerido para registrar el período al que corresponde la información del comprobante global.')