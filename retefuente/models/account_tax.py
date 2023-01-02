from odoo import api, fields, models

class AccountTax(models.Model):
    _inherit = ['account.tax']

    base = fields.Float('Base', help="Base para aplicar retención")
