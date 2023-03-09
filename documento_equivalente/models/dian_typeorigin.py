from odoo import models, fields, api


class TypeOfOrigin(models.Model):
    _name = 'dian.typeoforigin'
    _description = 'Tipo de procedencia'

    code = fields.Char(string='Codido', required=True)
    name = fields.Char(string='Descripción', required=True)