# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
# Since invoice amounts are unsigned, this is how we know if money comes in or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
}


class MultiInvoicePayment(models.TransientModel):
    _name = "customer.multi.payments"
    # _inherit = 'account.payment.register'

    memo = fields.Char(string='Memo')
    payment_date = fields.Date(required=True, default=fields.Date.context_today, string='Fecha')
    payment_type = fields.Selection(
        [('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Internal Transfer')],
        string='Payment Type', required=True, readonly=True, default="outbound")
    journal_id = fields.Many2one('account.journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    payment_method_id = fields.Many2one('account.payment.method', string='Tipo de método de pago',
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n"
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n"
                                             "Check: Pay bill by check and print it from Odoo.\n"
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n"
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")

    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             readonly=False, store=True,
                                             compute='_compute_payment_method_line_id',
                                             domain="[('id', 'in', available_payment_method_line_ids)]",
                                             help="Manual: Pay or Get paid by any method outside of Odoo.\n"
                                                  "Payment Acquirers: Each payment acquirer has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
                                                  "Check: Pay bills by check and print it from Odoo.\n"
                                                  "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
                                                  "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
                                                  "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line',
                                                         compute='_compute_payment_method_line_fields')
    hide_payment_method_line = fields.Boolean(
        compute='_compute_payment_method_line_fields',
        help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")

    final_amount = fields.Float(string='Cantidad total', \
                                compute='_final_amount', store=True)
    is_customer = fields.Boolean(string="Is Customer")
    customer_invoice_ids = fields.One2many('customer.invoice.lines', 'customer_wizard_id')
    supplier_invoice_ids = fields.One2many('supplier.invoice.lines', 'supplier_wizard_id')
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Empresa', readonly=True)
    payment_difference = fields.Float(string='Diferencia en pago', compute='_difference_amount', store=True)
    payment_difference_handling = fields.Selection(
        [('open', 'Mantener Abierto'), ('reconcile', 'Marcar la factura como totalmente pagada')],
        default='open', string="Payment Difference Handling", copy=False, required=True)
    writeoff_account_id = fields.Many2one('account.account', string="Difference Account",
                                          domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
                                          copy=False)
    writeoff_label = fields.Char(
        string='Journal Item Label',
        help='Change label of the counterpart that will hold the payment difference',
        default='Write-Off')

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_line_id(self):
        for wizard in self:
            available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines(wizard.payment_type)

            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                wizard.payment_method_line_id = False

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_line_fields(self):
        for wizard in self:
            wizard.available_payment_method_line_ids = wizard.journal_id._get_available_payment_method_lines(
                wizard.payment_type)
            if wizard.payment_method_line_id.id not in wizard.available_payment_method_line_ids.ids:
                # In some cases, we could be linked to a payment method line that has been unlinked from the journal.
                # In such cases, we want to show it on the payment.
                wizard.hide_payment_method_line = False
            else:
                wizard.hide_payment_method_line = len(wizard.available_payment_method_line_ids) == 1 \
                                                  and wizard.available_payment_method_line_ids.code == 'manual'

    @api.model
    def _compute_payment_amount(self, invoices, currency, journal, date=None):
        '''Compute the total amount for the payment wizard.

        :param invoices:    Invoices on which compute the total as an account.invoice recordset.
        :param currency:    The payment's currency as a res.currency record.
        :param journal:     The payment's journal as an account.journal record.
        :param date:        The payment's date as a datetime.date object.
        :return:            The total amount to pay the invoices.
        '''
        company = journal.company_id
        currency = currency or journal.currency_id or company.currency_id

        date = date or fields.Date.context_today

        if not invoices:
            return 0.0

        self.env['account.move'].flush(['move_type', 'currency_id'])
        self.env['account.move.line'].flush(['amount_residual', 'amount_residual_currency', 'move_id', 'account_id'])
        self.env['account.account'].flush(['user_type_id'])
        self.env['account.account.type'].flush(['type'])
        self._cr.execute('''
            SELECT
                move.move_type AS type,
                move.currency_id AS currency_id,
                SUM(line.amount_residual) AS amount_residual,
                SUM(line.amount_residual_currency) AS residual_currency
            FROM account_move move
            LEFT JOIN account_move_line line ON line.move_id = move.id
            LEFT JOIN account_account account ON account.id = line.account_id
            LEFT JOIN account_account_type account_type ON account_type.id = account.user_type_id
            WHERE move.id IN %s
            AND account_type.type IN ('receivable', 'payable')
            GROUP BY move.id, move.move_type
        ''', [tuple(invoices.ids)])
        query_res = self._cr.dictfetchall()

        total = 0.0
        for res in query_res:
            move_currency = self.env['res.currency'].browse(res['currency_id'])
            if move_currency == currency and move_currency != company.currency_id:
                total += res['residual_currency']
            else:
                total += company.currency_id._convert(res['amount_residual'], currency, company, date)
        return total

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            if self.journal_id.currency_id:
                self.currency_id = self.journal_id.currency_id

            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_method_line_ids.payment_method_id or self.journal_id.outbound_payment_method_line_ids.payment_method_id
            payment_methods_list = payment_methods.ids

            default_payment_method_id = self.env.context.get('default_payment_method_id')
            if default_payment_method_id:
                # Ensure the domain will accept the provided default value
                payment_methods_list.append(default_payment_method_id)
            else:
                self.payment_method_id = payment_methods and payment_methods[0] or False

            # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
            payment_type = self.payment_type in ('outbound', 'transfer') and 'outbound' or 'inbound'

            domain = {'payment_method_id': [('payment_type', '=', payment_type), ('id', 'in', payment_methods_list)]}

            return {'domain': domain}
        return {}

    @api.onchange('payment_difference')
    def _onchange_payment_difference(self):
        if self.payment_difference == 0:
            self.payment_difference_handling = 'open'

    @api.depends("customer_invoice_ids", "supplier_invoice_ids")
    def _difference_amount(self):
        for amount in self:
            total = 0
            if amount.customer_invoice_ids:
                for i in amount.customer_invoice_ids:
                    total += i.payment_diff - i.amount_to_pay
                amount.update({
                    'payment_difference': total
                })
            if amount.supplier_invoice_ids:
                for i in amount.supplier_invoice_ids:
                    total += i.payment_diff - i.amount_to_pay
                amount.update({
                    'payment_difference': total
                })

    @api.depends("customer_invoice_ids", "supplier_invoice_ids")
    def _final_amount(self):
        for amount in self:
            total = 0
            if amount.customer_invoice_ids:
                for i in amount.customer_invoice_ids:
                    total += i.amount_to_pay
                amount.update({
                    'final_amount': total
                })
            if amount.supplier_invoice_ids:
                for i in amount.supplier_invoice_ids:
                    total += i.amount_to_pay
                amount.update({
                    'final_amount': total
                })

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type:
            return {'domain': {'payment_method_id': [('payment_type', '=', self.payment_type)]}}

    def _get_invoices(self):
        return self.env['account.move'].browse(self._context.get('active_ids', []))

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        invoices = self.env[active_model].browse(active_ids)

        if any((invoice.state != 'posted' or invoice.payment_state not in ['not_paid', 'in_payment', 'partial']) for
               invoice in invoices):
            raise UserError(_("Solo puede registrar pagos para"
                              " facturas"))

        if any(MAP_INVOICE_TYPE_PARTNER_TYPE[inv.move_type] != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type]
               for inv in invoices):
            raise UserError(_("No puede mezclar facturas de clientes y proveedores"
                              " en un solo pago."))

        if any(inv.currency_id != invoices[0].currency_id for inv in invoices):
            raise UserError(_("Para pagar varias facturas a la vez,"
                              " debe usar la misma moneda."))

        if all(inv.amount_residual == 0 for inv in invoices):
            raise UserError(_("No hay facturas con pagos pendientes"))

        rec = {}
        inv_list = []
        if MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type] == 'customer':
            for inv in invoices:
                if inv.amount_residual > 0:
                    inv_list.append((0, 0, {
                        'invoice_id': inv.id,
                        'partner_id': inv.partner_id.commercial_partner_id.id,
                        'total_amount': inv.amount_total or 0.0,
                        'payment_diff': inv.amount_residual or 0.0,
                        'amount_to_pay': inv.amount_residual or 0.0,
                    }))
            rec.update({'customer_invoice_ids': inv_list,
                        'is_customer': True,
                        'payment_difference_handling': 'open',
                        'payment_date': datetime.now()})
        if MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type] == 'supplier':
            for inv in invoices:
                if inv.amount_residual > 0:
                    inv_list.append((0, 0, {
                        'invoice_id': inv.id,
                        'partner_id': inv.partner_id.commercial_partner_id.id,
                        'total_amount': inv.amount_total or 0.0,
                        'payment_diff': inv.amount_residual or 0.0,
                        'amount_to_pay': inv.amount_residual or 0.0,
                    }))
            rec.update({'supplier_invoice_ids': inv_list, 'is_customer': False})

        total_amount = sum(inv.amount_residual * MAP_INVOICE_TYPE_PAYMENT_SIGN[inv.move_type] for inv in invoices)
        # communication = ' '.join([ref for ref in invoices.mapped('reference') if ref])

        amount = self._compute_payment_amount(invoices, invoices[0].currency_id, invoices[0].journal_id)
        rec.update({
            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type],
            'payment_type': 'inbound' if amount > 0 else 'outbound',
        })
        return rec

    def get_new_payment_vals(self, payment):
        invoices = self.env['account.move'].browse(payment['invoice_list'])
        lines = invoices.line_ids
        values = {
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'date': self.payment_date,
            'ref': " ".join(i.payment_reference or i.ref or i.name for i in invoices),
            #"'reconciled_invoice_ids': [(6, 0, payment['invoice_list'])],
            'reconciled_invoices_type': 'invoice',
            'payment_type': self.payment_type,
            'amount': abs(payment['final_total']),
            'currency_id': invoices[0].currency_id.id,
            'partner_id': invoices[0].commercial_partner_id.commercial_partner_id.id,
            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type],
            'partner_bank_id': invoices[0].partner_bank_id.id,
        }
        if 'payment_diff' in payment:
            if not invoices[0].currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
                values['write_off_line_vals'] = {
                    'name': self.writeoff_label,
                    'amount': payment['payment_diff'],
                    'account_id': self.writeoff_account_id.id,
                }

        '''if 'payment_diff' in payment:
            is_zero = float_compare(payment['payment_diff'], 0.0, precision_rounding=invoices.currency_id.rounding)
            if self.payment_difference_handling == 'reconcile' and is_zero != 0:
                values['payment_difference_handling'] = self.payment_difference_handling
                #values['payment_difference'] = payment['payment_diff']
                values['writeoff_account_id'] = self.writeoff_account_id.id
                values['writeoff_label'] = self.writeoff_label'''

        return values

    def register_multi_payment(self):
        if self.customer_invoice_ids:
            for amount in self.customer_invoice_ids:
                if not amount.amount_to_pay > 0.0:
                    raise UserError(_("La cantidad debe ser estrictamente positiva \n"
                                      "Ingrese la cantidad recibida"))
        elif self.supplier_invoice_ids:
            for amount in self.supplier_invoice_ids:
                if not amount.amount_to_pay > 0.0:
                    raise UserError(_("La cantidad debe ser estrictamente positiva \n"
                                      "Ingrese la cantidad recibida"))
        else:
            raise UserError(_("Algo salió mal.... \n"))

        data = {}
        context = {}

        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        invoices = self.env[active_model].browse(active_ids)

        if self.is_customer:
            for inv in self.customer_invoice_ids:
                context.update({'is_customer': True})

                inv.payment_diff = inv.invoice_id.amount_residual - inv.amount_to_pay

                partner_id = str(inv.invoice_id.partner_id.commercial_partner_id.id)
                invoice_id = str(inv.invoice_id.id)

                is_zero = float_compare(inv.payment_diff, 0.0, precision_rounding=inv.invoice_id.currency_id.rounding)
                if self.payment_difference_handling == 'open':
                    '''if partner_id in data:
                        old_payment = data[partner_id]['final_total']
                        final_total = old_payment + inv.amount_to_pay

                        data[partner_id].update({
                            'partner_id': partner_id,
                            'final_total': final_total,
                            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[inv.invoice_id.move_type],
                            'payment_method_id': inv.payment_method_id,
                            'invoice_list': data[partner_id]['invoice_list'] + [inv.invoice_id.id]
                        })
                        data[partner_id]['inv_val'].update({
                            str(inv.invoice_id.id): {
                                'amount_to_pay': inv.amount_to_pay,
                                'payment_diff': inv.payment_diff,
                            }})
                    else:'''
                    data.update({invoice_id: {
                        'invoice_id': inv.invoice_id.id,
                        'partner_id': inv.partner_id.commercial_partner_id.id,
                        'total_amount': inv.total_amount,
                        'final_total': inv.amount_to_pay,
                        'invoice_list': [inv.invoice_id.id],
                        'inv_val': {str(inv.invoice_id.id): {
                            'amount_to_pay': inv.amount_to_pay,
                            'payment_diff': inv.payment_diff,
                        }}
                    }})
                elif self.payment_difference_handling == 'reconcile':
                    data.update({invoice_id: {
                        'invoice_id': inv.invoice_id.id,
                        'partner_id': inv.partner_id.commercial_partner_id.id,
                        'total_amount': inv.total_amount,
                        'final_total': inv.amount_to_pay,
                        'invoice_list': [inv.invoice_id.id],
                        'payment_diff': inv.payment_diff,
                        'amount_to_pay': inv.amount_to_pay,
                    }})

        else:
            for inv in self.supplier_invoice_ids:
                context.update({'is_customer': False})
                inv.payment_diff = inv.invoice_id.amount_residual - inv.amount_to_pay
                partner_id = str(inv.invoice_id.partner_id.commercial_partner_id.id)
                invoice_id = str(inv.invoice_id.id)
                if self.payment_difference_handling == 'open':
                    '''if partner_id in data:
                        old_payment = data[partner_id]['final_total']
                        final_total = old_payment + inv.amount_to_pay
                        data[partner_id].update({
                            'partner_id': partner_id,
                            'final_total': final_total,
                            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[inv.invoice_id.move_type],
                            'payment_method_id': inv.payment_method_id,
                            'invoice_list': data[partner_id]['invoice_list'] + [inv.invoice_id.id]
                        })
                        data[partner_id]['inv_val'].update({
                            str(inv.invoice_id.id): {
                                'amount_to_pay': inv.amount_to_pay,
                            }
                        })
                    else:'''
                    data.update({invoice_id: {
                        'invoice_id': inv.invoice_id.id,
                        'partner_id': inv.partner_id.commercial_partner_id.id,
                        'total_amount': inv.total_amount,
                        'final_total': inv.amount_to_pay,
                        'invoice_list': [inv.invoice_id.id],
                        'inv_val': {str(inv.invoice_id.id): {
                            'amount_to_pay': inv.amount_to_pay,
                        }}
                    }})
                elif self.payment_difference_handling == 'reconcile':
                    data.update({invoice_id: {
                        'invoice_id': inv.invoice_id.id,
                        'partner_id': inv.partner_id.commercial_partner_id.id,
                        'total_amount': inv.total_amount,
                        'final_total': inv.amount_to_pay,
                        'invoice_list': [inv.invoice_id.id],
                        'payment_diff': inv.payment_diff,
                        'amount_to_pay': inv.amount_to_pay,
                    }})


        context.update({'payment': data, 'payment_diff': self.payment_difference_handling})

        for payment in list(data):
            payment_ids = self.env['account.payment'].create(self.get_new_payment_vals(payment=data[payment]))
            payment_ids.with_context(payment=context).action_post()
            facturas = self.env[active_model].browse(data[payment]['invoice_list'])
            for fact in facturas:
                line_id = self.get_line_payment(fact, payment_ids.id).id
                fact.js_assign_outstanding_line(line_id)

    def get_line_payment(self, invoices, payment_id):
        for move in invoices:

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [
                ('payment_id', '=', payment_id),
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]


            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
            else:
                domain.append(('balance', '>', 0.0))

            return self.env['account.move.line'].search(domain)





class InvoiceLines(models.TransientModel):
    _name = 'customer.invoice.lines'

    customer_wizard_id = fields.Many2one('customer.multi.payments')
    invoice_id = fields.Many2one('account.move', required=True,
                                 string="Numero Factura")
    partner_id = fields.Many2one('res.partner', string='Cliente',
                                 related='invoice_id.partner_id',
                                 store=True, readonly=True, related_sudo=False)
    payment_method_id = fields.Many2one('account.payment.method', string='Tipo de pago')
    total_amount = fields.Float("Monto de la factura", required=True)
    amount_to_pay = fields.Float(string='Recibir monto')
    payment_diff = fields.Float(string='Monto restante', store=True, readonly=True)
    #amount_difference = fields.Float(string='Diferencia en pago', compute='_get_difference', store=True)

    '''@api.depends('amount_to_pay')
    def _get_difference(self):
        for rec in self:
            rec.amount_difference = rec.payment_diff - rec.amount_to_pay'''


class InvoiceLines(models.TransientModel):
    _name = 'supplier.invoice.lines'

    supplier_wizard_id = fields.Many2one('customer.multi.payments')
    invoice_id = fields.Many2one('account.move', required=True,
                                 string="Numero Factura")
    partner_id = fields.Many2one('res.partner', string='Proveedor',
                                 related='invoice_id.partner_id',
                                 store=True, readonly=True, related_sudo=False)
    payment_method_id = fields.Many2one('account.payment.method', string='Tipo de pago')
    total_amount = fields.Float("Monto de la factura", required=True)
    payment_diff = fields.Float(string='Monto restante', store=True, readonly=True)
    amount_to_pay = fields.Float(string='Recibir Monto')
