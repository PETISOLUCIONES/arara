# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        for line in self.order_line:
            line.onchange_product_id()
        super(PurchaseOrder, self).onchange_partner_id_warning()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    city_id = fields.Many2one('res.city', string='Ciudad', related='order_id.company_id.partner_id.city_id')

    @api.onchange('product_id')
    def onchange_product_id_ica(self):
        for line in self:
            if line.partner_id.is_ica:
                line.city_id = self.env.company.partner_id.city_id
                new_taxes = []
                product_taxes = line.product_id.supplier_taxes_id
                taxes = line.product_id.supplier_taxes_id.ids
                for tax in product_taxes:
                    if tax.is_ica and tax.city_id != line.city_id:
                        new_taxes.append(tax.id)
                if new_taxes:
                    for tax in new_taxes:
                        taxes.remove(tax)
                line.taxes_id = taxes
            else:
                taxes = line.product_id.supplier_taxes_id
                list = taxes.ids
                for tax in taxes:
                    if tax.is_ica == True:
                        list.remove(tax.id)
                line.taxes_id = list
