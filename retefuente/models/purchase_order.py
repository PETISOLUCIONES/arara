from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = ['purchase.order']

    def ValidarRetefuente(self):
        for rec in self:
            lineas = rec.order_line
            taxes_rtf = lineas.taxes_id.filtered(lambda m: m.type_tax.code == '06')
            for tax in taxes_rtf:
                sumatoria = 0
                for line in lineas:
                    if tax in line.taxes_id:
                        sumatoria += line.product_uom_qty * line.price_unit
                if tax.base or tax.base != 0:
                    if sumatoria < tax.base:
                        for line in lineas:
                            if tax in line.taxes_id:
                                line.write({'taxes_id': [(3, tax.id)]})
