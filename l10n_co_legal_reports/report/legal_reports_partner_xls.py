# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
import logging
_logger = logging.getLogger(__name__)

class PartnerReportXLS(models.AbstractModel):
    _name = 'report.l10n_co_legal_reports.partner_report_xls.xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Colombian Partner Report"

    def get_rows(self, data):
        legal_reports_account_id = data['form']['legal_reports_account_id']
        company_id = data['form']['company_id']
        date_to = data['form']['date_to']
        date_from = data['form']['date_from']

        acc_ids = []
        for lra in self.env['legal.reports.account'].browse(legal_reports_account_id[0]):
            for clra in lra.child_ids:
                for lines in clra.lines_ids:
                    acc_ids += lines.account_ids.ids

        if len(acc_ids) == 1:
            account_ids="(%s)" % (acc_ids[0])
        else:
            account_ids=tuple(acc_ids)

        SQL="""
            SELECT DISTINCT partner_id FROM account_move_line WHERE 
                account_id IN %s and
                move_id IN ( SELECT id FROM account_move WHERE
                    company_id = %s and
                    state = 'posted' and
                    date between '%s' and '%s'
                )
        """ % (account_ids, company_id[0], date_from, date_to) 
        self.env.cr.execute(SQL)
        SQL_RESULT=self.env.cr.fetchall()
        partner_ids = [x[0] for x in SQL_RESULT if x[0]]
        return partner_ids

    def get_columns(self, data, partner_id, clra, cm_partner_id):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        company_id = data['form']['company_id'][0]
        
        val = {
            'concept': clra.name,
            'partner_id': partner_id,
            'cols': [],
        }

        cols = []
        for lines in clra.lines_ids:
            if lines.account_ids:
                # Convert tuple 
                if len(lines.account_ids) == 1:
                    account_ids="(%s)" % (lines.account_ids.ids[0])
                else:
                    account_ids=tuple(lines.account_ids.ids)

                SQL_POST_IDS = """
                SELECT id FROM account_move 
                    WHERE state = 'posted' and
                    id IN (
                        SELECT DISTINCT move_id FROM account_move_line WHERE
                            company_id = %(company_id)s and
                            account_id IN %(account_ids)s and 
                            partner_id = %(partner_id)s and 
                            date <= '%(date_to)s' )
                """ % {
                    'company_id': company_id,
                    'account_ids': account_ids,
                    'partner_id': partner_id,
                    'date_to': date_to
                }
                self.env.cr.execute(SQL_POST_IDS)
                # Convert tuple
                SQL_POST_IDS = self.env.cr.fetchall()
                if len(SQL_POST_IDS) == 1:
                    SQL_POST_IDS = "(%s)" % (SQL_POST_IDS[0][0])
                else:
                    SQL_POST_IDS = tuple([x[0] for x in SQL_POST_IDS])
                if SQL_POST_IDS:
                    # debit and credit
                    SQL="""
                        SELECT partner_id, sum(debit) as debit, sum(credit) as credit FROM account_move_line WHERE
                            company_id = %(company_id)s and
                            move_id IN %(SQL_POST_IDS)s and
                            account_id IN %(account_ids)s and
                            partner_id = %(partner_id)s and
                            date between '%(date_from)s' and '%(date_to)s' GROUP BY partner_id
                        """ % {
                            'company_id': company_id,
                            'SQL_POST_IDS': SQL_POST_IDS,
                            'account_ids': account_ids,
                            'partner_id': partner_id,
                            'date_from': lines.balance and '1990-01-01' or date_from,
                            'date_to': date_to,
                        }


                    self.env.cr.execute(SQL)
                    report_balance = self.env.cr.dictfetchall()
                    c = {
                        'name': lines.name.name,
                        'operation': lines.operation,
                        'debit': report_balance and report_balance[0].get('debit', False) or 0.0,
                        'credit': report_balance and report_balance[0].get('credit', False) or 0.0,
                    }
                    if c['debit'] != 0.0 or c['credit'] != 0.0:
                        cols.append(c)
        if cols:
            val['cols'] = cols
            return val

        return False

    def get_field_value(self, value, field_name):
        if type( value ):
            return

    def _get_report_name(self, data):
        legal_reports_account_id = data['form']['legal_reports_account_id'][0]
        legal_report = self.env['legal.reports.account'].browse(legal_reports_account_id)
        report_name = "%s - %s" % (legal_report.name,legal_report.description)
        return self._get_report_complete_name(data, report_name)

    def generate_xlsx_report(self, workbook, data, lines):

        comp = self.env.user.company_id.name
        company_id = data['form']['company_id']
        date_to = data['form']['date_to']
        header = True
        #partner_ids = self.get_rows(data)

        sheet = workbook.add_worksheet('Informe por Terceros')
        #sheet.set_column('A1:Z1', 0)
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

        partner_column_id = data['form']['partner_column_id'][0]
        columns_ids = self.env['legal.reports.partner'].browse(partner_column_id).columns_ids

        partner_ids = self.get_rows(data)

        legal_reports_account_id = self.env['legal.reports.account'].browse(
            data['form']['legal_reports_account_id'][0]
        )

        colums_report = [x.name for x in legal_reports_account_id.rows_ids]
        columns_name = ['concepto'] + \
                       [x.name for x in columns_ids] + \
                       colums_report

                
        def write_line(rows, cols, h_col, data_partner):
            for index in data_partner:
                if index in ['debit', 'credit']:
                    continue

                if index == 'concept':
                    sheet.write(rows, 0, data_partner[index], font_size_8_r)
                elif index == 'partner_id':
                    partner_id = self.env['res.partner'].browse(data_partner[index])
                    cols = 1
                    for columns in columns_ids:
                        partner_value = columns.getfield(partner_id) 
                        sheet.write(rows, cols, partner_value, font_size_8_l)
                        cols += 1
                elif index == 'cols':
                    for x in colums_report:
                        data_cols = {}
                        for data_c in data_partner['cols']:
                            if x == data_c['name']:
                                data_cols = data_c
                                break

                        report_value = 0.0
                        if data_cols:
                            if data_cols['operation'] == 'debit':
                                report_value = data_cols['debit']

                            if data_cols['operation'] == 'credit':
                                report_value = data_cols['credit']

                            if data_cols['operation'] == 'debit_credit':
                                report_value = data_cols['debit'] - data_cols['credit']

                            if data_cols['operation'] == 'credit_debit':
                                report_value = data_cols['credit'] - data_cols['debit']

                        sheet.write(rows, cols, report_value, font_size_8_r)
                        cols += 1



       
        # Check cuantias menores
        cm_partner_id = self.env['res.partner'].search([('vat','=','222222222')])
        if not cm_partner_id:
            cm_partner_id = self.env['res.partner'].create({
                'name': 'Cuantias Menores',
                'vat': '222222222',
                'vat_type': '43',
                'company_type': 'company',
            })

        h_cols = len(columns_ids.ids) + 1
        cols = 0
        for columns in columns_name:
            sheet.write(0, cols, columns,format11)
            cols += 1

        rows = 1

        for clra in legal_reports_account_id.child_ids:
            val_cm = {
                'concept': clra.name,
                'partner_id': cm_partner_id.id,
                'initial': 0.0,
                'debit': 0.0,
                'credit': 0.0,
            }
            for partner in partner_ids:
                data_partner = self.get_columns(data, partner, clra, cm_partner_id)
                if data_partner:
                    if data_partner:
                        write_line(rows, h_cols, h_cols, data_partner)
                        rows += 1

            #if val_cm['debit']+val_cm['credit'] > 0:
            write_line(rows, h_cols, h_cols, val_cm)
            rows += 1

