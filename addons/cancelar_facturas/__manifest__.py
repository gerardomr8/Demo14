{ 
    'name': 'Cancelacion Facturas', 
    'description': 'Permite cancelar facturas', 
    'author': 'Jesus Salvador', 
    'depends': ['account'], 
    'application': True, 
    
    'data': [
        "security/ir.model.access.csv",
        "wizard/cancelar_factura_view.xml",
		"wizard/cancelar_pago_view.xml",
    ],
}

