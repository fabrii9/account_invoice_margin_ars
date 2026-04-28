{
    'name': 'Margen en Facturas ARS',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': 'Calcula margen en facturas de clientes considerando costo en USD y tipo de cambio ARS',
    'description': """
        Agrega columnas de costo en ARS y margen porcentual en las líneas de factura de clientes.
        El costo se toma del standard_price (USD, moneda de la compañía) y se convierte a ARS
        usando el tipo de cambio de la fecha de la factura.
    """,
    'author': 'El Alemán',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
