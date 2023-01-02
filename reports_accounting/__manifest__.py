# -*- coding: utf-8 -*-#
{
    'name': "Reportes de cuentas contables",

    'summary': """
        Reportes de cuentas contables""",

    'description': """
        Reportes de cuentas contables
    """,

    'author': "PETI Soluciones Productivas",
    'website': "http://www.peti.com.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'l10n_co_reports'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/general_actions.xml',
        'views/reports_views.xml',
        # 'views/report_execute_query.xml',
        'views/action_balance_report.xml',
        'views/action_books_reports.xml',
        'views/menus.xml',
    ]
}


