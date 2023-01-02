# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    agreement = fields.Char(string='Convenio')
    accountbank_type = fields.Selection(selection=[("saving", "Ahorros"), ("current", "Corriente")],
                                        string="Tipo de cuenta", required=True)
    reference = fields.Char(String='Referencia')