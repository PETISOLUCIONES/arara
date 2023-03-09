# -*- coding: utf-8 -*-
{
    'name': "documento_equivalente",

    'summary': """
        Modulo que adiciona funcionalidades a facturas de proveedor, 
        permitiendo enviar documento equivalente a la dian.""",

    'description': """
        Modulo que adiciona funcionalidades a facturas de proveedor, 
        permitiendo enviar documento equivalente a la dian
    """,

    'author': "PETI Soluciones Productivas",
    'website': "http://www.peti.com.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'facturacion_electronica'],

    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'security/ir_model_access.xml',
        'data/dian_type_of_origin.xml',
        'data/dian_form_gen_trans.xml',
        'data/dian_note_equivalent_document_concept.xml',
        'views/account_move.xml',
        'views/account_journal.xml',
        'views/account_move_reversal.xml',
        'views/templates.xml',
        'views/partner.xml',
    ],
}
