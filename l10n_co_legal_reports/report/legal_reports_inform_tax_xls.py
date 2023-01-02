# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
import logging
_logger = logging.getLogger(__name__)

class InformTaxReportXLS(models.AbstractModel):
    _name = 'report.l10n_co_legal_reports.inform_tax_xls.xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Colombian Tax Report"


    def get_tax(self, data):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        company_id = data['form']['company_id'][0]

        values = []
        tax_ids = []
        for invoice_type in ['%_refund','%_invoice']:
            SQL = """
                SELECT tax_line_id,SUM(price_total) AS amount, SUM(tax_base_amount) AS base FROM account_move_line WHERE move_id IN (
                    SELECT id FROM account_move
                        WHERE state IN ('draft', 'posted') and
                            company_id = %(company_id)s and
                            move_type LIKE '%(type)s' and
                            date between '%(date_from)s' and '%(date_to)s'
                ) AND not tax_line_id = 0 GROUP BY tax_line_id ORDER BY tax_line_id
                """ % {
                    'company_id': company_id,
                    'type': invoice_type,
                    'date_from': date_from,
                    'date_to': date_to,
            }
            self.env.cr.execute(SQL)
            for tax in self.env.cr.dictfetchall():
                id_tax_now = tax['tax_line_id']
                tax_id = self.env['account.tax'].browse(id_tax_now)
                itax_id = tax_id and tax_id.id or 0
                if tax['tax_line_id'] not in tax_ids:
                    tax_ids.append(itax_id)
                    values.append({
                        'tax_id': itax_id,
                        'name': tax_id and tax_id.name or 'Indefinido',
                        'tax': {
                            'amount': 0.0,
                            'base': 0.0,
                        },
                        'tax_refund': {
                            'amount': 0.0,
                            'base': 0.0,
                        },
                        'tax_total': {
                            'amount': 0.0,
                            'base': 0.0,
                        },
                    })
                for t in values:
                    if t['tax_id'] == itax_id:
                        if invoice_type == '%_refund':
                            t['tax_refund']['amount'] -= tax['amount']
                            t['tax_refund']['base'] -= tax['base']
                        else:
                            t['tax']['amount'] += tax['amount']
                            t['tax']['base'] += tax['base']
        return values

    """
    def _get_report_name(self, data):
        legal_reports_account_id = data['form']['legal_reports_account_id'][0]
        legal_report = self.env['legal.reports.account'].browse(legal_reports_account_id)
        report_name = "%s - %s" % (legal_report.name,legal_report.description)
        return self._get_report_complete_name(data, report_name)
    """

    def generate_xlsx_report(self, workbook, data, lines):


        sheet = workbook.add_worksheet('Informe por Terceros')
        sheet.set_column('B1:G1', 0)
        sheet.set_column('A1:A1', 30)
        #####sheet.Columns.AutoFit()

        format0 = workbook.add_format({'font_size': 20, 'align': 'center', 'bold': True})
        format1 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format11 = workbook.add_format({'font_size': 12, 'align': 'center', 'bold': True})
        format21 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format3 = workbook.add_format({'bottom': True, 'top': True, 'font_size': 12})
        format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True})
        font_size_8 = workbook.add_format({'font_size': 8, 'align': 'center'})
        font_size_8_l = workbook.add_format({'font_size': 8, 'align': 'left'})
        font_size_8_r = workbook.add_format({'font_size': 8, 'align': 'right','num_format': '0.00'})
        red_mark = workbook.add_format({'font_size': 8, 'bg_color': 'red'})
        justify = workbook.add_format({'font_size': 12})

        """
        format3.set_align('center')
        justify.set_align('justify')
        format1.set_align('center')
        red_mark.set_align('center')

        sheet.merge_range(1, 7, 2, 11, 'Informe por Terceros', format0)
        sheet.merge_range(3, 7, 3, 11, comp, format11)
        sheet.merge_range(4, 7, 4, 11, date_range, format21)
        sheet.merge_range(5, 3, 5, 21, report_name, format21)
        """

        
        # Check cuantias menores

        h_cols = 0
        cols = 0
        columns_name = ['concepto','impuesto', 'base', 'impuesto', 'base', 'impuesto', 'base']

        sheet.merge_range('B1:C1', 'Facturado', format11)
        sheet.merge_range('D1:E1', 'Nota Crédito', format11)
        sheet.merge_range('F1:G1', 'Total', format11)
        for columns in columns_name:
            sheet.write(1, cols, columns, format11)
            cols += 1
        rows = 2
        h_cols = 0
        for tax in self.get_tax(data):
            cols = h_cols
            sheet.write(rows, cols, tax['name'], font_size_8_l)
            cols += 1
            tax['tax_total']['amount'] = tax['tax']['amount'] + tax['tax_refund']['amount']
            tax['tax_total']['base'] = tax['tax']['base'] + tax['tax_refund']['base']            
            for t in ['tax','tax_refund','tax_total']:
                sheet.write(rows, cols, tax[t]['amount'], font_size_8_r)
                cols += 1
                sheet.write(rows, cols, tax[t]['base'], font_size_8_r)
                cols += 1
            rows += 1

