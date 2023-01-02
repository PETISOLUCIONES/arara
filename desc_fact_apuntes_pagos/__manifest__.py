# -*- coding: utf-8 -*-
{
    'name': "Descripción-Factura y Apuntes-Pagos",

    'summary': """
        - Añade la descripción por diferencia de pago en las facturas,
        - Añade los apuntes contables en los recibos de pago.""",

    'description': """
        En el reporte de facturas añade la descripción en las facturas 
        de proveedores cuando existe una diferencia de pago.
        
        En el reporte de recibo de pago añade los apuntes contables asociados
        a dicho recibo de pago.
    """,

    'author': "PETI Soluciones Productivas",
    'website': "https://peti.com.co",

    'category': 'Uncategorized',
    'version': '13.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account_accountant'],

    # always loaded
    'data': [
        'reports/report_invoice_document_with_description.xml',
        'reports/report_payment_receipt_document_with_journal_items.xml',
    ],
}
