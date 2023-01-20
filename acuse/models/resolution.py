from odoo import api, fields, models
from odoo.exceptions import Warning


class Resolution(models.Model):
    _inherit = 'dian.resolution'

    document_type = fields.Selection(selection_add=[('factura_compra', 'Factura de compra')],
                                     ondelete={'factura_compra': 'set default'})
