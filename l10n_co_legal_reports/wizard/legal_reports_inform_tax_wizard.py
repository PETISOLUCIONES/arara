# -*- coding: utf-8 -*-
from odoo import api, fields, models

class RetentionReportInformTaxWizard(models.TransientModel):
    _name = 'legal.reports.inform.tax.wizard'
    _description = 'Informes Legales de Impuestos y Retenciones Wizard'

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.user.company_id,
        string='Compañia',
        required=False,
        ondelete='cascade',
    )
    date_range_id = fields.Many2one(
        comodel_name='date.range',
        string='Rango de Fecha',
    )
    date_from = fields.Date(
        string="Desde",
        required=True
    )

    date_to = fields.Date(
        string="Hasta",
        required=True
    )

    @api.onchange("date_range_id", )
    def _onchange_date_range_id(self):
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    def export_xlsx(self):
        context = self._context
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'legal.reports.inform.tax.wizard'
        datas['form'] = self.read()[0]
        
        report = self.env['ir.actions.report'].sudo()._get_report_from_name('l10n_co_legal_reports.inform_tax_xls.xlsx')
        report.report_file = "%s - Impuestos y Retenciones %s-%s" % \
                    (self.company_id.name, datas['form']['date_from'], datas['form']['date_to'])


        if context.get('xls_export'):
            return self.env.ref('l10n_co_legal_reports.inform_tax_xlsx').report_action(self, data=datas)


