# -*- coding: utf-8 -*-

{
    'name': 'Colombian Campos Base V15',
    'version': '13.0.0.0.1',
    'category': 'Hidden/Dependency',
    'description': """
Campos Base Colombia
=========================================
    """,

    'author': 'José Luis Vizcaya López',
    'company': 'José Luis Vizcaya López',
    'maintainer': 'José Luis Vizcaya López',
    'website': 'https://vizcaya.mi-erp.app',
    'depends': ['base', 'l10n_latam_base'],
    'data': [
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/l10n_co_res_partner.xml',
        'views/ciiu.xml',
        'security/ir.model.access.csv',
        'data/ciiu.csv',
    ],
    'images': ['images/1_partner_vat.jpeg'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
