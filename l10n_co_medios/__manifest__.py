# -*- coding: utf-8 -*-
{
    'name': "Medios Magnéticos",

    'summary': """
        Reportes de medios magneticos.""",

    'description': """
        Reportes de medios magneticos.
    """,

    'author': 'José Luis Vizcaya López',
    'company': 'José Luis Vizcaya López',
    'maintainer': 'José Luis Vizcaya López',
    'website': 'https://vizcaya.mi-erp.app',
    'category': 'Account',
    "version": "13.0.1.0.0",
    'depends': ['account'],
    'data': [
        # security
        'security/ir.model.access.csv',
        'data/1001.xml',
        'data/1003.xml',
        'data/1004.xml',
        'data/1005.xml',
        'data/1006.xml',
        'data/1007.xml',
        'data/1008.xml',
        'data/1009.xml',
        'data/1010.xml',
        'data/1011.xml',
        'data/1012.xml',
        'data/2276.xml',
        'data/art_2.xml',
        'data/art_4.xml',
        'data/art_6.xml',
        'data/account.account.tag.csv',
        'data/magnetic.media.lines.csv',
        'data/magnetic.media.lines.concepts.csv',
        # views
        'views/magnetic_media_views.xml',
    ],
    'demo': [],
    "price": 1500,
    "currency": "USD",
    'installable': True,
    'application': False,
    'auto_install': False,
    "license": "OPL-1",
}
