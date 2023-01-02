# -*- coding: utf-8 -*-
# from odoo import http


# class ContactosRues(http.Controller):
#     @http.route('/contactos_rues/contactos_rues', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/contactos_rues/contactos_rues/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('contactos_rues.listing', {
#             'root': '/contactos_rues/contactos_rues',
#             'objects': http.request.env['contactos_rues.contactos_rues'].search([]),
#         })

#     @http.route('/contactos_rues/contactos_rues/objects/<model("contactos_rues.contactos_rues"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('contactos_rues.object', {
#             'object': obj
#         })
