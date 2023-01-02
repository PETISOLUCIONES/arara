{
    'name': 'Colombian - Accounting Legal Reports',
    'version': '1.1',
    'description': """
Accounting legal reports for Colombia
================================
    """,
    'author': ['Carlos Fonseca, (www.2la.co)'],
    'category': 'Accounting',
    'depends': [
        'account',
        'web',
        'report_xlsx',
        'date_range'
    ],
    'images': [
        'static/description/icon.png',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/legal_reports_tax_data.xml',
        #'data/legal_reports_account_data.xml',
        'data/legal_reports_partner_data.xml',
        'report/legal_reports_tax_report_templates.xml',
        'views/legal_reports_menu.xml',
        'wizard/legal_reports_tax_wizard_view.xml',
        'views/legal_reports_tax_view.xml',
        'views/legal_reports_account_view.xml',
        'views/legal_reports_partner_columns_view.xml',
        'wizard/legal_reports_inform_tax_wizard_view.xml',
        'wizard/legal_reports_partner_wizard_view.xml',
    ],
    'demo': [],
    'auto_install': True,
    'installable': True,
    'licenses': 'OEEL-1 (120.00 USD)',
}
