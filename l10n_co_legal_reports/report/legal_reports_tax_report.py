# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, Warning

import logging
_logger = logging.getLogger(__name__)


class ReportTaxCertification(models.AbstractModel):
    _name = 'report.l10n_co_legal_reports.teplate_tax_certification'
    _description = "Colombian Tax Certification Report"

    @api.model
    def _get_report_values(self, docids, data=None):

        docs = []
        docs_ids = []
        partner_doc = {}

        tax_ids = data.get('tax_ids', False)
        partner_ids = data.get('partner_ids', False)
        company_id = data.get('id_company', False)
        date_from = data['wizard_values'].get('date_from', False)
        date_to = data['wizard_values'].get('date_to', False)
        if len(tax_ids) == 1:
            tax_ids = [tax_ids[0]]
        else:
            tax_ids = [x for x in tax_ids]

        for partner_id in partner_ids:
            SQL = """
                SELECT id FROM account_move
                    WHERE state IN ('draft', 'posted') and
                        move_type LIKE 'in_%%' and
                        company_id=%(company_id)s and
                        partner_id=%(partner_id)s and
                        date between '%(date_from)s' and '%(date_to)s'
                """ % {
                'company_id': company_id,
                'partner_id': partner_id,
                'date_from': date_from,
                'date_to': date_to,
                'tax_ids': tax_ids,
            }

            self.env.cr.execute(SQL)
            invoice_ids = self.env.cr.fetchall()

            if len(invoice_ids) == 0:
                continue

            if len(invoice_ids) == 1:
                invoice_ids = [invoice_ids[0][0]]
            else:
                invoice_ids = [x[0] for x in invoice_ids]

            invoice_ids = self.env['account.move'].browse(invoice_ids)

            if not invoice_ids:
                raise ValidationError(
                    'No existen datos para "%s"' % (
                        self.env['res.partner'].browse(partner_id).name
                    )
                )

            lines = []
            for invoice in invoice_ids:
                for tax in invoice.invoice_line_ids.tax_ids:
                    if tax.id not in tax_ids:
                        continue
                    base = tax.base
                    amount = tax.amount
                    if invoice.move_type.find('refund') > 0:
                        base *= -1
                        amount *= -1
                    not_lines_exist = True
                    for l in lines:
                        if l['tax_id'] == tax.id:
                            l['base'] += base
                            l['amount'] += amount
                            not_lines_exist = False
                            break
                    if not_lines_exist:
                        lines.append({
                            'tax_id': tax.id,
                            'tax_name': tax.name,
                            # 'currency_id': tax.tax_line_id,
                            'base': base,
                            'amount': amount,
                        })

            partner_doc = {
                'partner_id': self.env['res.partner'].browse(partner_id).id,
                'lines': [],
            }
            if lines:
                partner_doc['lines'] = lines
                docs.append(partner_doc)
            else:
                raise ValidationError(
                    'No existen datos del informe para "%s"' % (
                        self.env['res.partner'].browse(partner_id).name
                    )
                )

        docs = [doc for doc in docs if doc['lines']]
        # docs = self.env["legal.tax.reports"].browse([docs_ids])
        if not docs:
            raise ValidationError(_('No se encontraron datos para procesar.'))

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': self.env.company,
            'date_from': date_from,
            'date_to': date_to,
            # 'data': data['wizard_values'],
            'data': data,
            'datos': docs,
            'lineas': docs[0]['lines'],
            # 'company_id': data['company_id'],
        }


# class ReportTaxCertificationsLines(models.AbstractModel):
#     _name = 'legal.reports.tax.data.lines'
#
#     relacion_id = fields.Many2one('legal.tax.reports', 'Lineas de impuestos')
#
#     tax_name = fields.Char("Nombre")
#
#     base = fields.Float(required=True, digits=(16, 4), default=0.0)
#
#     amount = fields.Float(required=True, digits=(16, 4), default=0.0)


# class ReportTaxCertifications(models.AbstractModel):
#     _name = 'legal.reports.tax.data'
#
#     partner_id = fields.Many2one('res.partner', string="Partner", ondelete="set null")
#
#     line_ids = fields.One2many('legal.reports.tax.data.lines', 'relacion_id', string="nombre")
#
#     def update_tax(self, vals):
#         if vals.get('partner_id'):
#             partner_id = vals.get('partner_id')
#             id_partner = False
#             try:
#                 id_partner = self.env['account.tax'].browse(
#                     partner_id
#                 )
#                 vals.update({
#                     'partner_id': [(4, id_partner.id)]
#                 })
#             except:
#                 _logger.debug('Error en el filtro "%s"' % (partner_id))
#                 raise ValidationError(
#                     'Error en el filtro "%s"' % (partner_id)
#                 )
#         return vals
#
#     @api.model
#     def create(self, vals):
#         vals = self.update_tax(vals)
#         return super(ReportTaxCertifications, self).create(vals)
#
#     def write(self, vals):
#         return super(ReportTaxCertifications, self).create(vals)
