# -*- coding: utf-8 -*-
{
    'name': "Product Category Reference",

    'summary': """
        Product Category Reference
        """,

    'description': """
        Product Category Reference
    """,

    'author': "Todoo SAS",
    'contributors': ['Pater fg@todoo.co'],
    'website': "http://www.todoo.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tools',
    'version': '14.1.1',

    # any module necessary for this one to work correctly
    'depends': ['product','sale_timesheet'],

    # always loaded
    'data': [
        'views/product_view.xml',
    ],
}
