# -*- coding: utf-8 -*-
{
    'name': "Facturacion Electronica",

    'summary': """
        Facturación electronica""",

    'description': """
       Facturación electronica
    """,

    'author': "PETI Soluciones Productivas",
    'website': "http://www.peti.com.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'l10n_co_location',  'account_debit_note', 'sale', 'account', 'od_journal_sequence', 'l10n_co_base_nit', 'l10n_latam_base'],

    # always loaded
    'data': [
        'security/ir_model_access.xml',
        'security/group_user_access.xml',
        #'security/ir.model.access.csv',
        'data/res_country_data.xml',
        'data/dian_fiscal_regimen.xml',
        'data/dian_type_tax.xml',
        'data/dian_operation_type.xml',
        'data/dian_company_type.xml',
        'data/dian_document_type.xml',
        'data/dian_fiscal_responsibility.xml',
        'data/dian_paymentmethod.xml',
        'data/dian_credit_note_concept.xml',
        'data/dian_debit_note_concept.xml',
        'data/dian_payment_mean.xml',
        'data/mail_template_electronic.xml',
        'data/product_product.xml',
        'data/ir_cron_data.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/mail_invoice.xml',
        'views/resolution_views.xml',
        'views/ir_sequence.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
