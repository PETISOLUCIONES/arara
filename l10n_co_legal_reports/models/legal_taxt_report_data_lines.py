from odoo import models, fields, api
from odoo.exceptions import ValidationError, Warning

import logging
_logger = logging.getLogger(__name__)


class ReportTaxCertificationsLines(models.AbstractModel):
    _name = 'legal.reports.tax.data.lines'

    relacion_id = fields.Many2one('legal.tax.reports', 'Lineas de impuestos')

    tax_name = fields.Char("Nombre")

    base = fields.Float(required=True, digits=(16, 4), default=0.0)

    amount = fields.Float(required=True, digits=(16, 4), default=0.0)



