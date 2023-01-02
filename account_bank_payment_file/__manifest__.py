# -*- coding: utf-8 -*-
{
    'name': "Archivo plano bancos",

    'summary': """
        Genera archivo plano del banco para pago de proveedores""",

    'description': """
        Genera archivo plano del banco para pago de proveedores
    """,

    'author': "PETI Soluciones Productivas",
    'website': "http://www.peti.com.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'cuentas_bancarias', 'l10n_co_location'],

    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'views/account_payment_view.xml',
        'views/res_partner_bank_view.xml',
    ],
}
