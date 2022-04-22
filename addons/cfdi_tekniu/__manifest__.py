# -*- coding: utf-8 -*-
{
    'name': 'Pasarela Tekniu',
    'summary': """
       Facturacion México Tekniu 
    """,
    'description': """
    """,
    'author': "Tekniu",
    'website': "https://tekniu.mx",

    'category': 'Other',
    'version': '1.0',
    'application': False,
    'external_dependencies': {
        'python': [
        ],
    },
    'depends': [
     'l10n_mx_edi',
    ],
    # always loaded
    'data': [
        'data/cfdi.xml',
        'data/datos_pac.xml',
    ],
    'demo': [
    ],
}
