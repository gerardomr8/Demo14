# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "cfdi_tekniu_40",
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': "Modulo complemento para el timbrado y cancelacion en 4.0",
    'description': "Modulo complemento para el timbrado y cancelacion en 4.0",
    'license': 'LGPL-3',
    'author': 'Tekniu: Pascual Neftalí Chávez Campos',
    'website': 'https://soluciones.tekniu.mx/',
    'depends': ['l10n_mx_edi', 'cfdi_tekniu'],
    'demo': [],
    'data': 
        [
            'data/account_edi_data.xml',
            'data/cfdi.xml',
            'views/invoice.xml',
            'views/partner.xml',
            'views/factura_40.xml',
            'views/impuestos.xml'
        ],
    'installable': True,
    'Application': True,
    'Auto_install': True,
}
