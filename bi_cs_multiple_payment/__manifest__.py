# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.
{
	'name': 'Multiple Invoice Payment and Credit Notes(Customer/Supplier) Payment in odoo',
	'version': '13.0.0.1',
	'category': 'Accounting',
	'sequence': 15,
    'summary': 'Apps help to make single payment for multiple invoices multi invoice payment multiple bill payment mass bill payment mass invoice payment multiple invoices payment single payment from multiple invoice pay all bill at once single payment for invoice',
    'description': """
    	Multiple Invoice Payment
    	Multiple Customer and Supplier payment
		multiple Payment partial
		full invoices payment
		partially invoice payment
		multi invoice payment 
		single payment for multiple invoices
		Multiple one payment 
		Multiple bill payment 
		mass bill payment
		Multiple Invoice Payment
		Multiple Credit Notes Payment
		partial Credit Note Payment
    	Multiple customer invoice payment Multiple supplier invoice payment.
    	single payment from multiple invoice
    	multiple customer invoice payment
		partial pay all invoice together 
		partial pay all bill at once  
		partial bill payment Multiple invoices payment
		multiple vendor bills payment multiple bill payment in odo
		multiple bill payment in odoo apps
		multiple invoice payment multiple invoice payment in odoo 
		multiple invoice payment in odoo apps, odoo app, odoo apps, odoo installation, 
		odoo migration, odoo plugin, odoo training, Multiple payments for invoice
		payment multiple invoices  payment multiple invoices in odoo payment multiple invoice in odoo apps
    	multiple supplier invoice payment
    	multiple payment option
    	Multiple payment invoice
    	multi invoice payment
    	multi sale order payment
    	mass invoice payment
    	many invoice payment, payment register for multiple invoice
    	multiple bill payment, multiple vendor bill payment, multiple vendor bill single payment
    	multiple payment receipt for multiple invoice,  multiple payment receipt for many invoice
    	partial invoice payment partial payment on invoice partial invoice order invoice partial payment
    	partial refund payment half payment half invoice payment invoice partially payment
    	partially invoice payment partial refund invoice partial refund payment partial vendor payment 
    	partial vendor bills payment partial vendor refund payment partial customer payment parial invoices payment

""",
	'author' : 'Browseinfo',
	'website': 'https://www.browseinfo.in',
	'price': 19,
    'currency': "EUR",
	'depends': ['account','account_payment'],
	'data': [
		'wizard/multi_invoice_payment_views.xml',
		'views/multi_payment_views.xml',
		'security/ir.model.access.csv',
	],
	'demo': [],
	'css': [],
	'installable': True,
	'auto_install': False,
	'application': False,
	'live_test_url':'https://youtu.be/_aFgGvqxEys',
    "images":['static/description/Banner.png'],
}
