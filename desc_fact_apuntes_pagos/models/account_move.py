# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Campo que relaciona una factura con todos sus pagos
    payments = fields.Many2many(
        comodel_name="account.payment",
        compute='_compute_payment_ids'
    )
