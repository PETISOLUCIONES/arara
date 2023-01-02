from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = ['account.move']

    def ValidarRetefuente(self):
        for rec in self:
            lineas = rec.invoice_line_ids
            taxes_rtf = lineas.tax_ids.filtered(lambda m: m.type_tax.code == '06')
            for tax in taxes_rtf:
                sumatoria = 0
                for line in lineas:
                    if tax in line.tax_ids:
                        sumatoria += line.quantity * line.price_unit
                if tax.base or tax.base != 0:
                    if sumatoria < tax.base:
                        for line in lineas:
                            if tax in line.tax_ids:
                                line.write({'tax_ids': [(3, tax.id)]})
                                dic_line = {'product_id': line.product_id,
                                            'tax_ids': line.tax_ids.filtered(lambda line: line.id != tax.id),
                                            'price_unit': line.price_unit,
                                            'quantity': line.quantity,
                                            'discount': line.discount,
                                            'sale_line_ids': line.sale_line_ids}
                                rec.write({'invoice_line_ids': [(3, line.id)]})
                                rec.write({'invoice_line_ids': [(0, 0, dic_line)]})

