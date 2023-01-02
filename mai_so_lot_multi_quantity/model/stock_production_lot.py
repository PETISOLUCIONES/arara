from odoo import api, fields, models, _


class stock_production_lot(models.Model):
    _inherit = 'stock.production.lot'

    def name_get(self):
        res = []
        for record in self:
            lot_name = record.name or ''
            quants = record.env['stock.quant'].search([('product_id', '=', record.product_id.id), ('lot_id', '=', record.id), ('location_id.usage', '=', 'internal')])
            qty_avalibity = 0
            for quant in quants:
                qty_avalibity += quant.quantity - quant.reserved_quantity
            lot_with_qty = lot_name + "(" + str(qty_avalibity) + " " + record.product_uom_id.name + ")"
            res.append((record.id, lot_with_qty))
        return res
