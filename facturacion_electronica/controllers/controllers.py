# -*- coding: utf-8 -*-
# from odoo import http


# class FacturacionMonitor(http.Controller):
#     @http.route('/facturacion_monitor/facturacion_monitor/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/facturacion_monitor/facturacion_monitor/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('facturacion_monitor.listing', {
#             'root': '/facturacion_monitor/facturacion_monitor',
#             'objects': http.request.env['facturacion_monitor.facturacion_monitor'].search([]),
#         })

#     @http.route('/facturacion_monitor/facturacion_monitor/objects/<model("facturacion_monitor.facturacion_monitor"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('facturacion_monitor.object', {
#             'object': obj
#         })
