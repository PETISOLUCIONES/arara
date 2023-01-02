# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_ica = fields.Boolean(string='Actividades ICA')
    # activity_city_ids = fields.One2many('res.activity.city.ica', 'partner_id', string='Ciudad y Actividad')

