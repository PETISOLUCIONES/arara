# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCity(models.Model):
    _inherit = 'res.city'

    code = fields.Char(string='Codigo DIAN', required=True)



class ResState(models.Model):
    _inherit = 'res.country.state'

    dian_state_code = fields.Char(string='Código de estado')



class Bank(models.Model):
    _inherit = 'res.bank'

    city_id = fields.Many2one('res.city', string='City Ref', ondelete='restrict')

    
    @api.onchange('city_id')
    def onchange_city(self):
        return {'value': {'state': self.city_id.state_id.id,
                          'city': self.city_id.name,
                          'country_id': self.city_id.state_id.country_id.id}}


class Company(models.Model):
    _inherit = 'res.company'

    city_id = fields.Many2one('res.city', string='City Ref', ondelete='restrict')

    
    @api.onchange('city_id')
    def onchange_city(self):
        return {'value': {'state_id': self.city_id.state_id.id,
                          'city': self.city_id.name,
                          'country_id': self.city_id.state_id.country_id.id}}

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('city_id')
    def onchange_city(self):
        return {'value': {'state_id': self.city_id.state_id.id,
                          'city': self.city_id.name,
                          'country_id': self.city_id.state_id.country_id.id}}