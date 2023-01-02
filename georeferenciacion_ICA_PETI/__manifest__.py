# -*- coding: utf-8 -*-
{
    'name': "Georeferenciacion ICA",

    'summary': """
        Este modulo calcula los impuestos ICA teniendo como base la actividad y la ubicacion
        del tercero
        """,

    'description': """
        Este modulo calcula los impuestos ICA teniendo como base la actividad y la ubicacion
        del tercero
    """,

    'author': "Todoo SAS",
    'contributors': ['Carlos Guio fg@todoo.co'],
    'website': "http://www.todoo.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tools',
    'version': '13.1',

    # any module necessary for this one to work correctly
    'depends': ['facturacion_electronica', 'purchase', 'sale'],

    # always loaded
    'data': [
        'views/account_tax.xml',
        'views/res_partner.xml',
        'views/account_move.xml',
        'views/purchase_order.xml',
        'views/sale_order.xml',
    ],
}
