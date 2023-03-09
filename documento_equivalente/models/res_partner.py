from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    type_of_origin_id = fields.Many2one('dian.typeoforigin', string='Tipo de procedencia')
