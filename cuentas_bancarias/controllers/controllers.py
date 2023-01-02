# -*- coding: utf-8 -*-
# from odoo import http


# class CuentasBancarias(http.Controller):
#     @http.route('/cuentas_bancarias/cuentas_bancarias/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cuentas_bancarias/cuentas_bancarias/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cuentas_bancarias.listing', {
#             'root': '/cuentas_bancarias/cuentas_bancarias',
#             'objects': http.request.env['cuentas_bancarias.cuentas_bancarias'].search([]),
#         })

#     @http.route('/cuentas_bancarias/cuentas_bancarias/objects/<model("cuentas_bancarias.cuentas_bancarias"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cuentas_bancarias.object', {
#             'object': obj
#         })
