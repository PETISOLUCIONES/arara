from odoo import models, fields, api
from odoo.exceptions import ValidationError, Warning

import logging
_logger = logging.getLogger(__name__)


class ReportTaxCertifications(models.AbstractModel):
    _name = 'legal.reports.tax.data'

    partner_id = fields.Many2one('res.partner', string="Partner")

    line_ids = fields.One2many('legal.reports.tax.data.lines', 'relacion_id', string="nombre")

    def update_tax(self, vals):
        if vals.get('partner_id'):
            partner_id = vals.get('partner_id')
            id_partner = False
            try:
                id_partner = self.env['account.tax'].browse(
                    partner_id
                )
                vals.update({
                    'partner_id': [(4, id_partner.id)]
                })
            except:
                _logger.debug('Error en el filtro "%s"' % ( partner_id ))
                raise ValidationError(
                    'Error en el filtro "%s"' % ( partner_id )
                )
        return vals

    @api.model
    def create(self, vals):
        vals = self.update_tax(vals)
        return super(ReportTaxCertifications, self).create(vals)

    def write(self, vals):
        return super(ReportTaxCertifications, self).create(vals)

