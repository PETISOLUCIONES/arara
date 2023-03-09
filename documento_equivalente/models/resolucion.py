# -*- coding: utf-8 -*-

from odoo import models, fields, api


#Agrega la opción de seleccionar documento equivalente para resolución
class Resolution(models.Model):
    _inherit ='dian.resolution'

    document_type = fields.Selection(selection_add=[("05", "Documento Equivalente"),
                                                    ("95", "Nota Documento Equivalente")],
                                     ondelete={'05': 'set default', '95': 'set default'})