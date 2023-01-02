# -*- coding: utf-8 -*-
{
    'name': "Retefuente",

    'summary': """
        Valida el monto para aplicar o no la retención en la fuente""",

    'description': """
       Valida el monto para aplicar o no la retención en la fuente
    """,

    'author': "PETI Soluciones Productivas",
    'website': "http://www.peti.com.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'account', 'facturacion_electronica'],

    # always loaded
    'data': [
        'views/account_move.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml',
        'views/account_tax.xml',
    ],
}
