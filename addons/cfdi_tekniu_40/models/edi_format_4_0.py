from email.policy import default
from odoo import models, fields, modules, tools, api, _, SUPERUSER_ID
from odoo.tools.xml_utils import _check_with_xsd
from io import BytesIO
from datetime import datetime

import logging 
import base64
import requests

from lxml import etree, objectify
from werkzeug.urls import url_quote
from os.path import join
import json
from zeep import Client
from zeep.transports import Transport

_log = logging.getLogger(__name__)


class ProductsFactura40(models.Model):
    _inherit = 'product.template'

    obj_impuesto = fields.Selection([
        ('01',	'No objeto de impuesto.'),
        ('02',	'Sí objeto de impuesto.'),
        ('03',	'Sí objeto del impuesto y no obligado al desglose.')], string = 'Es objeto de impuesto:', 
        help = 'Atributo requerido para expresar si la operación comercial es objeto o no de impuesto')

    @api.onchange('obj_impuesto', 'taxes_id')
    def on_change_state(self):
        
        if len(self.taxes_id) > 1:
            self.taxes_id = self.taxes_id[1]

        #Si el producto esta como no objeto de impuesto y tiene asignado un impuesto erroneo
        if (self.obj_impuesto == '01' or not self.obj_impuesto) and not self.taxes_id.tipo and self.taxes_id:
                self.taxes_id = self.env['account.tax'].search([('tipo','=',True)],limit=1)
                #raise UserError('El producto debe ser "No objeto de impuesto"')
                
        elif self.obj_impuesto != '01' and (self.taxes_id.tipo or not self.taxes_id):
                self.taxes_id = self.env['account.tax'].search([('tipo','=',False)],limit=1)
                #raise UserError('El producto debe ser "Si objeto de impuesto"')

class AccountEdiFormat40(models.Model):
    _inherit = 'account.edi.format'

    version_cfdi = fields.Char(default = '0')

    def _check_move_configuration(self, move):
        errors = super()._check_move_configuration(move)
        if move.version_cfdi == '4.0':
            self.version_cfdi = '4.0'
            return errors
        elif move.version_cfdi == '3.3':
            self.version_cfdi = '3.3'
            return errors


    def _l10n_mx_edi_get_common_cfdi_values(self, move):
        # if self.version_cfdi == '3.3':
        #    return super()._l10n_mx_edi_get_common_cfdi_values(move)
        # if self.version_cfdi == '4.0':
        res = super()._l10n_mx_edi_get_common_cfdi_values(move)
        customer = move.partner_id if move.partner_id.type == 'invoice' else move.partner_id.commercial_partner_id
        supplier = move.company_id.partner_id.commercial_partner_id
        res['DomicilioFiscalReceptor'] = customer.zip
        res['RegimenFiscalReceptor'] = customer.receptor_mx_edi_fiscal_regime_40
        res['Exportacion'] = move.exportacion_cfdi
        res['Periodicidad'] = move.periodicidad_cfdi
        res['Meses'] = move.meses_cfdi
        res['Año'] = move.year_cfdi
        res['origin_type'] = move.tipo_relacion_cfdi
        res['UsoCFDI'] = move.uso_cfdi
        
        #_log.critical('===============RES.keys():%s' %res.keys())
        return res 

    # def _needs_web_services(self):
        # _log.critical = ('web services')
        # _log.critical = (self.version_cfdi)
        # return self.code == 'cfdi_4_0' or super()._needs_web_services() 
        # if self.version_cfdi == '3.3':
        #    return self.code == 'cfdi_3_3' or super()._needs_web_services()
        # if self.version_cfdi == '4.0':
        #    return self.code == 'cfdi_4_0' or super()._needs_web_services() 

    @api.model
    def _load_xsd_files(self, url):

        # if self.code == 'cfdi_3_3':
            # return super()._load_xsd_files(url)
        # 
        # if self.code == 'cfdi_4_0':
        fname = url.split('/')[-1]
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            logging.getLogger(__name__).info(
                'I cannot connect with the given URL.')
            return ''
        try:
            res = objectify.fromstring(response.content)
        except etree.XMLSyntaxError as e:
            logging.getLogger(__name__).info(
                'You are trying to load an invalid xsd file.\n%s', e)
            return ''
        namespace = {'xs': 'http://www.w3.org/2001/XMLSchema'}
        if fname == 'cfdv40.xsd':
            # This is the xsd root
            res = self._load_xsd_complements(res)
        sub_urls = res.xpath('//xs:import', namespaces=namespace)
        for s_url in sub_urls:
            s_url_catch = self._load_xsd_files(s_url.get('schemaLocation'))
            s_url.attrib['schemaLocation'] = url_quote(s_url_catch)
        try:
            xsd_string = etree.tostring(res, pretty_print=True)
        except etree.XMLSyntaxError:
            logging.getLogger(__name__).info('XSD file downloaded is not valid')
            return ''
        if not xsd_string:
            logging.getLogger(__name__).info('XSD file downloaded is empty')
            return ''
        env = api.Environment(self._cr, SUPERUSER_ID, {})
        xsd_fname = 'xsd_cached_%s' % fname.replace('.', '_')
        attachment = env.ref('l10n_mx_edi.%s' % xsd_fname, False)
        filestore = tools.config.filestore(self._cr.dbname)
        if attachment:
            return join(filestore, attachment.store_fname)
        attachment = env['ir.attachment'].create({
            'name': xsd_fname,
            'datas': base64.encodebytes(xsd_string),
        })
        # Forcing the triggering of the store_fname
        attachment._inverse_datas()
        self._cr.execute(
            """INSERT INTO ir_model_data
            (name, res_id, module, model, noupdate)
            VALUES (%s, %s, 'l10n_mx_edi', 'ir.attachment', true)""", (
                xsd_fname, attachment.id))
        return join(filestore, attachment.store_fname)


    @api.model
    def _load_xsd_attachments(self):
        # if self.code == 'cfdi_3_3':
            # return super()._load_xsd_attachments()
        # 
        # if self.code == 'cfdi_4_0':
        url = 'http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd'
        xml_ids = self.env['ir.model.data'].search(
            [('name', 'like', 'xsd_cached_%')])
        xsd_files = ['%s.%s' % (x.module, x.name) for x in xml_ids]
        for xsd in xsd_files:
            self.env.ref(xsd).unlink()
        self._load_xsd_files(url)

    def _l10n_mx_edi_export_invoice_cfdi(self, invoice):

        # if self.code == 'cfdi_3_3':
            # return super()._l10n_mx_edi_export_invoice_cfdi(invoice)
        # 
        # if self.code == 'cfdi_4_0':

        # == CFDI values ==
        cfdi_values = self._l10n_mx_edi_get_invoice_cfdi_values(invoice)

        # == Generate the CFDI ==
        cfdi = self.env.ref('cfdi_tekniu_40.cfdiv40')._render(cfdi_values)

        decoded_cfdi_values = invoice._l10n_mx_edi_decode_cfdi(cfdi_data = cfdi)

        cfdi_cadena_crypted = cfdi_values['certificate'].sudo().get_encrypted_cadena(decoded_cfdi_values['cadena'])

        decoded_cfdi_values['cfdi_node'].attrib['Sello'] = cfdi_cadena_crypted

        # == Optional check using the XSD ==
        xsd_attachment = self.env.ref('cfdi_tekniu_40.xsd_cached_cfdv40_xsd', False)
        xsd_datas = base64.b64decode(xsd_attachment.datas) if xsd_attachment else None

        if xsd_datas:
            try:
                with BytesIO(xsd_datas) as xsd:
                    _check_with_xsd(decoded_cfdi_values['cfdi_node'], xsd)
            except (IOError, ValueError):
                _log.info(_('The xsd file to validate the XML structure was not found'))
            except Exception as e:
                return {'errors': str(e).split('\\n')}
        return {
            'cfdi_str': etree.tostring(decoded_cfdi_values['cfdi_node'], pretty_print = True, xml_declaration = True, encoding = 'UTF-8'),
        }

    def _create_invoice_cfdi_attachment(self, invoice, data):
        # if self.code == 'cfdi_3_3':
            # return super()._create_invoice_cfdi_attachment(invoice, data)
        # if self.code == 'cfdi_4_0':
        cfdi_filename = ('%s-%s-MX-Invoice-4.0.xml' % (invoice.journal_id.code, invoice.payment_reference)).replace('/', '')
        description = _('Mexican invoice CFDI generated for the %s document.') % invoice.name
        return self._create_cfdi_attachment(cfdi_filename, description, invoice, data)

class ResCompany40(models.Model):
    _inherit = 'account.tax'

    tipo = fields.Boolean(string="Sin impuesto", default=False)


class AccountEdiFormatCFDI40(models.Model): #Moficaciones pasarela de tekiu y valores del XML para facturas
    _inherit = 'account.edi.format'

    #Modificacion: Calculo del atributo base
    def _l10n_mx_edi_get_invoice_cfdi_values(self, invoice):
        ''' Doesn't check if the config is correct so you need to call _l10n_mx_edi_check_config first.

        :param invoice:
        :return:
        '''
        cfdi_date = datetime.combine(
            fields.Datetime.from_string(invoice.invoice_date),
            invoice.l10n_mx_edi_post_time.time(),
        ).strftime('%Y-%m-%dT%H:%M:%S')

        cfdi_values = {
            **self._l10n_mx_edi_get_common_cfdi_values(invoice),
            'document_type': 'I' if invoice.move_type == 'out_invoice' else 'E',
            'currency_name': invoice.currency_id.name,
            'payment_method_code': (invoice.l10n_mx_edi_payment_method_id.code or '').replace('NA', '99'),
            'payment_policy': invoice.l10n_mx_edi_payment_policy,
            'cfdi_date': cfdi_date,
        }

        # ==== Invoice Values ====

        invoice_lines = invoice.invoice_line_ids.filtered(lambda inv: not inv.display_type)

        if invoice.currency_id == invoice.company_currency_id:
            cfdi_values['currency_conversion_rate'] = None
        else:
            sign = 1 if invoice.move_type in ('out_invoice', 'out_receipt', 'in_refund') else -1
            total_amount_currency = sign * invoice.amount_total
            total_balance = invoice.amount_total_signed
            cfdi_values['currency_conversion_rate'] = total_balance / total_amount_currency

        if invoice.partner_bank_id:
            digits = [s for s in invoice.partner_bank_id.acc_number if s.isdigit()]
            acc_4number = ''.join(digits)[-4:]
            cfdi_values['account_4num'] = acc_4number if len(acc_4number) == 4 else None
        else:
            cfdi_values['account_4num'] = None

        if cfdi_values['customer'].country_id.l10n_mx_edi_code != 'MEX' and cfdi_values['customer_rfc'] not in ('XEXX010101000', 'XAXX010101000'):
            cfdi_values['customer_fiscal_residence'] = cfdi_values['customer'].country_id.l10n_mx_edi_code
        else:
            cfdi_values['customer_fiscal_residence'] = None

        # ==== Invoice lines ====

        cfdi_values['invoice_line_values'] = []
        for line in invoice_lines:
            cfdi_values['invoice_line_values'].append(self._l10n_mx_edi_get_invoice_line_cfdi_values(invoice, line))

        # ==== Totals ====

        cfdi_values['total_amount_untaxed_wo_discount'] = sum(vals['total_wo_discount'] for vals in cfdi_values['invoice_line_values'])
        cfdi_values['total_amount_untaxed_discount'] = sum(vals['discount_amount'] for vals in cfdi_values['invoice_line_values'])

        # ==== Taxes ====

        cfdi_values['tax_details_transferred'] = {}
        cfdi_values['tax_details_withholding'] = {}
        for vals in cfdi_values['invoice_line_values']:
            for tax_res in vals['tax_details_transferred']:
                cfdi_values['tax_details_transferred'].setdefault(tax_res['tax'], {
                    'base': 0.0,                                                        ####
                    'tax': tax_res['tax'],
                    'tax_type': tax_res['tax_type'],
                    'tax_amount': tax_res['tax_amount'],
                    'tax_name': tax_res['tax_name'],
                    'total': 0.0,
                })
                cfdi_values['tax_details_transferred'][tax_res['tax']]['total'] += tax_res['total']
                cfdi_values['tax_details_transferred'][tax_res['tax']]['base'] += tax_res['base']   ####
            for tax_res in vals['tax_details_withholding']:
                cfdi_values['tax_details_withholding'].setdefault(tax_res['tax'], {
                    'base': 0.0,                                                        ####
                    'tax': tax_res['tax'],
                    'tax_type': tax_res['tax_type'],
                    'tax_amount': tax_res['tax_amount'],
                    'tax_name': tax_res['tax_name'],
                    'total': 0.0,
                })
                cfdi_values['tax_details_withholding'][tax_res['tax']]['total'] += tax_res['total']
                cfdi_values['tax_details_withholding'][tax_res['tax']]['base'] += tax_res['base']   ####

        cfdi_values['tax_details_transferred'] = list(cfdi_values['tax_details_transferred'].values())
        cfdi_values['tax_details_withholding'] = list(cfdi_values['tax_details_withholding'].values())
        cfdi_values['total_tax_details_transferred'] = sum(vals['total'] for vals in cfdi_values['tax_details_transferred'])
        cfdi_values['total_tax_details_withholding'] = sum(vals['total'] for vals in cfdi_values['tax_details_withholding'])

        return cfdi_values
