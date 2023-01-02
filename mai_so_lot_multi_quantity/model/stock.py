from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_round, float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    lot_ids = fields.Many2many('stock.production.lot', string="Crate", copy=False)
    assign_lot = fields.Boolean(string='Assign Lot')

    def create_stock_move_line(self, lista_lotes):
        parcial = False
        en_cero = False
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for move in self:

            if move.move_line_ids:
                if move.sale_line_id and move.sale_line_id.lot_ids:
                    # asignar los lotes desde las S0
                    move.move_line_ids.unlink()
                    monto_total = move.product_uom_qty
                    for lot_id in move.sale_line_id.lot_ids:
                        monto_reservar = 0
                        qty_reserved = 0
                        for quant in lot_id.quant_ids:
                            qty_reserved += quant.reserved_quantity
                        qty_available = lot_id.product_qty - qty_reserved
                        if qty_available < monto_total:
                            monto_reservar = qty_available
                            monto_total = monto_total - monto_reservar
                        else:
                            monto_reservar = monto_total
                        if monto_reservar > 0:
                            quants = move.env['stock.quant']._gather(move.product_id, move.location_id,
                                                                     lot_id=lot_id, strict=False)

                            for quant in quants:
                                disponible = quant.quantity - quant.reserved_quantity
                                if float_compare(disponible, monto_reservar, precision_digits=rounding) != -1:
                                    vals = {
                                        'move_id': move.id,
                                        'product_id': move.product_id.id,
                                        'product_uom_id': move.product_uom.id,
                                        'location_id': quant.location_id.id,
                                        'location_dest_id': move.location_dest_id.id,
                                        'picking_id': move.picking_id.id,
                                        'lot_id': lot_id.id,
                                        'state': 'assigned',
                                        'product_uom_qty': monto_reservar
                                    }
                                    self.env['stock.move.line'].create(vals)
                                    quants = move.env['stock.quant']._update_reserved_quantity(
                                        move.product_id, quant.location_id, monto_reservar, lot_id=lot_id, strict=False)
                                    break

                else:
                    move.move_line_ids.unlink()
                    for l in lista_lotes:
                        if l:
                            monto_reservar = 0
                            monto_total = move.product_uom_qty
                            qty_reserved = 0
                            for quant in l.quant_ids:
                                qty_reserved += quant.reserved_quantity
                            qty_available = l.product_qty - qty_reserved
                            if qty_available < monto_total:
                                monto_reservar = qty_available
                                monto_total = monto_total - monto_reservar
                            else:
                                monto_reservar = monto_total
                            if monto_reservar > 0:
                                quants = move.env['stock.quant']._gather(move.product_id, move.location_id,
                                                                         lot_id=l, strict=False)

                                for quant in quants:
                                    disponible = quant.quantity - quant.reserved_quantity
                                    if float_compare(disponible, monto_reservar, precision_digits=rounding) != -1:
                                        vals = {
                                            'move_id': move.id,
                                            'product_id': move.product_id.id,
                                            'product_uom_id': move.product_uom.id,
                                            'location_id': quant.location_id.id,
                                            'location_dest_id': move.location_dest_id.id,
                                            'picking_id': move.picking_id.id,
                                            'lot_id': l.id,
                                            'state': 'assigned',
                                            'product_uom_qty': monto_reservar
                                        }
                                        self.env['stock.move.line'].create(vals)
                                        quants = move.env['stock.quant']._update_reserved_quantity(
                                            move.product_id, quant.location_id, monto_reservar, lot_id=l, strict=False)
                                        break


            if move.product_uom_qty != move.reserved_availability:
                parcial = True
        if parcial:
            # verificar todos en cero
            todos = True
            for move in self:
                if move.reserved_availability != 0:
                    todos = False
            if todos:
                move.state = 'confirmed'
            else:
                move.state = 'partially_available'
        else:
            move.state = 'assigned'

    @api.model
    def _action_assign(self):
        lista_lotes = []

        for move in self:
            for l in move.move_line_ids:
                if l.lot_id:
                    lista_lotes.append(l.lot_id)

        res = super(StockMove, self)._action_assign()
        for move in self:
            if move.move_line_ids:
                if move.sale_line_id and move.sale_line_id.lot_ids:
                    move.create_stock_move_line(lista_lotes)
                    # if not move.assign_lot:
                else:
                    if len(lista_lotes) > 0:
                        move.create_stock_move_line(lista_lotes)
        return res

    '''def create_stock_move_line(self):
        for move in self:
            if move.move_line_ids:
                if move.sale_line_id and move.sale_line_id.lot_ids:
                    move.move_line_ids.unlink()
                    for lot_id in move.sale_line_id.lot_ids:
                        qty_sold = move.product_uom_qty
                        qty_reserved = 0
                        qty_reser = 0
                        for quant in lot_id.quant_ids:
                            qty_reserved += quant.reserved_quantity
                        qty_available = lot_id.product_qty - qty_reserved
                        if qty_available < qty_sold:
                            qty_reser = qty_available
                        else:
                            qty_reser = qty_sold

                        vals = {
                                'move_id': move.id,
                                'product_id': move.product_id.id,
                                'product_uom_id': move.product_uom.id,
                                'location_id': move.location_id.id,
                                'location_dest_id': move.location_dest_id.id,
                                'picking_id': move.picking_id.id,
                                'lot_id': lot_id.id,
                                'state': 'assigned',
                                'product_uom_qty': qty_reser,
                                }
                        self.env['stock.move.line'].create(vals)
                        quants = move.env['stock.quant']._update_reserved_quantity(
                            move.product_id, move.location_id, qty_sold, lot_id=lot_id, strict=True)
     
    def _action_assign(self):
        for move in self:
            if not move.assign_lot:
                move.create_stock_move_line()
                move.assign_lot = True
        res = super(StockMove, self)._action_assign()
        return res

    def _do_unreserve(self):
        res = super(StockMove, self)._do_unreserve()
        for move in self:
            if move.assign_lot:
                move.assign_lot = False
        return res'''
