from odoo import models, fields, api


class DianFormGenTrans(models.Model):
    _name = 'dian.formgentrans'
    _description = '16.1.6 Forma de generación y transmisión: cbc: DescriptionCode; cbc: Description '

    code = fields.Char(string='Codido', required=True)
    name = fields.Char(string='Descripción', required=True)