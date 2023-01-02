import logging

from odoo import api, fields, models
from odoo.exceptions import Warning



class Resolution(models.Model):
    _name = 'dian.resolution'
    _description = 'Electronic invoice resolution'

    name = fields.Char(string="Nombre", compute='_compute_name')

    # Range Resolution DIAN
    document_type = fields.Selection(selection=[("01", "Factura electronica de venta"),
                                                ("02", "Factura de exportación"),
                                                ("03", "Documento electrónico de transmisión – tipo 03"),
                                                ("04", "Factura electrónica de Venta - tipo 04"),
                                                ("91", "Nota Crédito"),
                                                ("92", "Nota Débito"),
                                                ("00", "Factura de Venta (No electrónica)")],
                                     string="Tipo de documento", default="01", required=True)
    resolution_prefix = fields.Char(string="Prefijo")
    resolution_resolution = fields.Char(string="Resolución")
    resolution_resolution_date = fields.Date(string="Fecha de la resolución")
    resolution_technical_key = fields.Char(string="Llave tecnica")
    resolution_from = fields.Integer(string="Desde", required=True)
    resolution_to = fields.Integer(string="Hasta", required=True)
    resolution_date_from = fields.Date(string="Fecha Desde")
    resolution_date_to = fields.Date(string="Fecha Hasta")




    def _compute_name(self):
        for rec in self:
            if rec.document_type:
                value = dict(rec._fields['document_type'].selection).get(rec.document_type)
                rec.name = str(rec.resolution_prefix) + ' - ' + \
                           value + ' [' + rec.document_type + ']'

    @api.model
    def create(self, vals):
        return super(Resolution, self).create(vals)

    #@api.multi
    def write(self, vals):
        return super(Resolution, self).write(vals)



    #@api.multi
    def unlink(self):
        return super(models.Model, self).unlink()

