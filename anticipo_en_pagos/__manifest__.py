# -*- coding: utf-8 -*-
{
    'name': "Anticipo en Pagos",

    'summary': """
        permite crear tipos de anticipos""",

    'description': """
        permite crear tipos de anticipos en pagos
    """,

    'author': "PETI Soluciones Productivas",
    'website': "http://www.peti.com.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['facturacion_electronica'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/ir_model_access.xml',
        'views/anticipo_en_pagos_view.xml',
    ],

}
