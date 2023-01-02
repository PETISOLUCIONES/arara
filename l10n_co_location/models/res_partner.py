
from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('city_id')
    def _onchange_city_id(self):
        for rec in self:
            if rec.city_id:
                rec.write({'city': rec.city_id.name, 'zip': rec.city_id.code})
            else:
                rec.write({'city': '', 'zip': ''})