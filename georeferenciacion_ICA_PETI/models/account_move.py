# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    city_id = fields.Many2one('res.city', string='Ciudad', store=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.city_id = self.partner_id.city_id
        for line in self.invoice_line_ids:
            line.city_id = self.city_id
            line.partner_id = self.partner_id
            line.recompute_tax_line = True
            line._onchange_product_id()
        super(AccountMove, self)._onchange_partner_id()

    @api.model_create_multi
    def create(self, vals):
        for am in vals:
            am['city_id'] = self.env['res.partner'].search([('id', '=', am.get('partner_id'))]).city_id.id
        res = super(AccountMove, self).create(vals)
        return res

    def write(self, vals):
        for rec in self:
            if rec.move_type in ["out_invoice", "out_refund", "in_invoice", "in_refund"]:
                if not vals.get('city_id'):
                    vals['city_id'] = rec.env['res.partner'].search([('id', '=', rec.partner_id.id if not vals.get(
                        'partner_id') else vals['partner_id'])]).city_id.id
        res = super(AccountMove, self).write(vals)
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    city_id = fields.Many2one('res.city', string='Ciudad', store=True)

    @api.onchange('product_id', 'city_id')
    def _onchange_product_id(self):
        super(AccountMoveLine, self)._onchange_product_id()
        for line in self:
            line.city_id = line.move_id.city_id if not line.city_id else line.city_id
            if line.partner_id.is_ica:
                new_taxes = []
                product_taxes = line.product_id.taxes_id if line.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt'] else line.product_id.supplier_taxes_id
                taxes = line.product_id.taxes_id.ids if line.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt'] else line.product_id.supplier_taxes_id.ids
                for tax in product_taxes:
                    if tax.is_ica and tax.city_id != line.city_id:
                        new_taxes.append(tax.id)
                if new_taxes:
                    for tax in new_taxes:
                        taxes.remove(tax)
                line.tax_ids = taxes
            else:
                new_taxes = []
                product_taxes = line.product_id.taxes_id if line.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt'] else line.product_id.supplier_taxes_id
                taxes = line.product_id.taxes_id.ids if line.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt'] else line.product_id.supplier_taxes_id.ids
                for tax in product_taxes:
                    if tax.is_ica:
                        new_taxes.append(tax.id)
                if new_taxes:
                    for tax in new_taxes:
                        taxes.remove(tax)
                line.tax_ids = taxes

    @api.model_create_multi
    def create(self, vals):
        if vals:
            for ln in vals:
                ln['city_id'] = self.env['account.move'].search([('id', '=', ln.get('move_id'))]).city_id.id
        res = super(AccountMoveLine, self).create(vals)
        return res

    def write(self, vals):
        if not vals.get('city_id'):
            vals['city_id'] = self.env['res.partner'].search([('id', '=', self.move_id.partner_id.id if not vals.get(
                'partner_id') else vals['partner_id'])]).city_id.id
        res = super(AccountMoveLine, self).write(vals)
        return res