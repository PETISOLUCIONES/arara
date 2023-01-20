# -*- coding: utf-8 -*-
{
    'name': "Envío de acuse a la DIAN",

    'summary': """
            Envíar a la DIAN el acuse de las facturas recibidas de los proveedores.""",

    'description': """
        Envíar a la DIAN el acuse de las facturas recibidas de los proveedores.
    """,

    'author': "PETI Soluciones Productivas",
    'website': "http://www.peti.com.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'account',
        'facturacion_electronica',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_company.xml',
        'views/account_move.xml',
        'views/resolution.xml',
        'views/account_journal.xml',
        'wizard/acuse_wizard.xml',
    ],
}
