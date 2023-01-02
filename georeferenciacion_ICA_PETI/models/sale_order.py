# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    city_id = fields.Many2one('res.city', string='Ciudad',)

    @api.onchange('partner_id')
    def onchange_partner_shipping_id(self):
        for record in self:
            record.city_id = record.partner_id.city_id
            for line in record.order_line:
                line.city_id = record.city_id
                line.product_id_change()
        super(SaleOrder, self).onchange_partner_shipping_id()

    @api.model
    def create(self,vals):
        vals['city_id'] = self.env['res.partner'].search([('id', '=', vals.get('partner_id'))]).city_id.id
        res = super(SaleOrder, self).create(vals)
        return res

    def write(self, vals):
        if not vals.get('city_id'):
            vals['city_id'] = self.env['res.partner'].search([('id', '=', self.partner_id.id if not vals.get('partner_id') else vals['partner_id'])]).city_id.id
        res = super(SaleOrder, self).write(vals)
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    city_id = fields.Many2one('res.city', string='Ciudad')

    @api.onchange('product_id')
    def product_id_change(self):
        super(SaleOrderLine, self).product_id_change()
        for line in self:
            line.city_id = line.order_id.city_id if not line.city_id else line.city_id
            if line.order_id.partner_id.is_ica:
                new_taxes = []
                product_taxes = line.product_id.taxes_id
                taxes = line.product_id.taxes_id.ids
                for tax in product_taxes:
                    if tax.is_ica and tax.city_id != line.city_id:
                        new_taxes.append(tax.id)
                if new_taxes:
                    for tax in new_taxes:
                        taxes.remove(tax)
                line.tax_id = taxes
            else:
                taxes = line.product_id.taxes_id
                list = taxes.ids
                for tax in taxes:
                    if tax.is_ica == True:
                        list.remove(tax.id)
                line.tax_id = list
            