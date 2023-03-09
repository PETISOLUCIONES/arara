# -*- coding: utf-8 -*-
# from odoo import http


# class DocumentoEquivalente(http.Controller):
#     @http.route('/documento_equivalente/documento_equivalente/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/documento_equivalente/documento_equivalente/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('documento_equivalente.listing', {
#             'root': '/documento_equivalente/documento_equivalente',
#             'objects': http.request.env['documento_equivalente.documento_equivalente'].search([]),
#         })

#     @http.route('/documento_equivalente/documento_equivalente/objects/<model("documento_equivalente.documento_equivalente"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('documento_equivalente.object', {
#             'object': obj
#         })
