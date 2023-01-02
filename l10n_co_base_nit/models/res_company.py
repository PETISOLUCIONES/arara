# -*- coding: utf-8 -*-

from odoo import models, fields

class res_company(models.Model):
    _inherit = 'res.company'

    vat_type = fields.Selection(related='partner_id.vat_type',
                                string='VAT type', readonly=True)
    vat_vd = fields.Char(related='partner_id.vat_vd', string='VD', readonly=True)
    company_registry = fields.Char('Company Registry', related='partner_id.vat', size=64)
