# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class account_payment(models.Model):
    _inherit = "account.payment"

    '''def action_post(self):
        if 'payment' in self._context:
            account_move = self.env['account.move'].with_context(default_type='entry')
            for rec in self:
                if len(rec.reconciled_invoice_ids) > 1:
                    if rec.state != 'draft':
                        raise UserError(_("Only a draft payment can be posted."))

                    if any(inv.state != 'posted' for inv in rec.reconciled_invoice_ids):
                        raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

                    if not rec.name:                        
                        if rec.payment_type == 'transfer':
                            sequence_code = 'account.payment.transfer'
                        else:
                            if rec.partner_type == 'customer':
                                if rec.payment_type == 'inbound':
                                    sequence_code = 'account.payment.customer.invoice'
                                if rec.payment_type == 'outbound':
                                    sequence_code = 'account.payment.customer.refund'
                            if rec.partner_type == 'supplier':
                                if rec.payment_type == 'inbound':
                                    sequence_code = 'account.payment.supplier.refund'
                                if rec.payment_type == 'outbound':
                                    sequence_code = 'account.payment.supplier.invoice'
                        rec.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=rec.date)
                        if not rec.name and rec.payment_type != 'transfer':
                            raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

                    rec_values = rec._prepare_payment_moves()

                    move_name = []
                    for invoices in rec.reconciled_invoice_ids:
                        for value in rec_values:
                            current_pay_data = value[str(invoices.id)]
                            moves = account_move.create(current_pay_data)
                            moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()

                            if moves:
                                move_name.append(moves.name)
                            
                            if rec.payment_type in ('inbound', 'outbound'):
                                if invoices:
                                    (moves[0] + invoices).line_ids \
                                        .filtered(lambda line: not line.reconciled and line.account_id == rec.destination_account_id)\
                                        .reconcile()
                            elif rec.payment_type == 'transfer':
                                moves.mapped('line_ids')\
                                    .filtered(lambda line: line.account_id == rec.company_id.transfer_account_id)\
                                    .reconcile()
                    _name = self._get_move_name_transfer_separator().join(move_name)
                    rec.write({'state': 'posted', 'move_name': _name})
                    return True
                else:
                    return super(account_payment,self).action_post()
        return super(account_payment,self).action_post()'''

    def _prepare_payment_moves(self):
        if 'payment' in self._context:
            all_move_vals = []
            for payment in self:
                company_currency = payment.company_id.currency_id
                move_names = payment.move_name.split(payment._get_move_name_transfer_separator()) if payment.move_name else None

                # Compute amounts.
                write_off_amount = payment.payment_difference_handling == 'reconcile' and -payment.payment_difference or 0.0
                
                payment_data = self._context.get('payment')
                payment_diff = payment_data.get('payment_diff')
                inv_data = payment_data.get('payment')
                if payment_diff == 'reconcile':
                    return super(account_payment, self)._prepare_payment_moves()
                else:
                    if len(inv_data[str(payment.partner_id.id)]['invoice_list']) > 1:
                        records = {}
                        for inv_move in inv_data[str(payment.partner_id.id)]['invoice_list']:
                            paymennt_value = inv_data[str(payment.partner_id.id)]['inv_val'][str(inv_move)]
                            amount = paymennt_value.get('amount_to_pay')
                            payment_difference = paymennt_value.get('payment_diff')


                            if payment.payment_type in ('outbound', 'transfer'):
                                counterpart_amount = amount
                                liquidity_line_account = payment.journal_id.default_debit_account_id
                            else:
                                counterpart_amount = -amount
                                liquidity_line_account = payment.journal_id.default_credit_account_id

                            # Manage currency.
                            if payment.currency_id == company_currency:
                                # Single-currency.
                                balance = counterpart_amount
                                write_off_balance = write_off_amount
                                counterpart_amount = write_off_amount = 0.0
                                currency_id = False
                            else:
                                # Multi-currencies.
                                balance = payment.currency_id._convert(counterpart_amount, company_currency, payment.company_id, payment.date)
                                write_off_balance = payment.currency_id._convert(write_off_amount, company_currency, payment.company_id, payment.date)
                                currency_id = payment.currency_id.id


                            # Manage custom currency on journal for liquidity line.
                            if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
                                # Custom currency on journal.
                                liquidity_line_currency_id = payment.journal_id.currency_id.id
                                liquidity_amount = company_currency._convert(
                                    balance, payment.journal_id.currency_id, payment.company_id, payment.date)

                            else:
                                # Use the payment currency.
                                liquidity_line_currency_id = currency_id
                                liquidity_amount = counterpart_amount

                            name = [inv.name for inv in payment.invoice_ids if inv.id == inv_move]

                            rec_pay_line_name = ''
                            if payment.payment_type == 'transfer':
                                rec_pay_line_name = payment.name
                            else:
                                if payment.partner_type == 'customer':
                                    if payment.payment_type == 'inbound':
                                        rec_pay_line_name += _("Customer Payment")
                                    elif payment.payment_type == 'outbound':
                                        rec_pay_line_name += _("Customer Credit Note")
                                elif payment.partner_type == 'supplier':
                                    if payment.payment_type == 'inbound':
                                        rec_pay_line_name += _("Vendor Credit Note")
                                    elif payment.payment_type == 'outbound':
                                        rec_pay_line_name += _("Vendor Payment")
                                if payment.invoice_ids:
                                    rec_pay_line_name += ': %s' % ', '.join(name)

                            # Compute 'name' to be used in liquidity line.
                            if payment.payment_type == 'transfer':
                                liquidity_line_name = _('Transfer to %s') % payment.destination_journal_id.name
                            else:
                                liquidity_line_name = payment.name

                            # ==== 'inbound' / 'outbound' ====

                            move_vals = {
                                'date': payment.date,
                                'ref': payment.communication,
                                'journal_id': payment.journal_id.id,
                                'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
                                'partner_id': payment.partner_id.id,
                                'line_ids': [
                                    # Receivable / Payable / Transfer line.
                                    (0, 0, {
                                        'name': rec_pay_line_name,
                                        'amount_currency': counterpart_amount + write_off_amount,
                                        'currency_id': currency_id,
                                        'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                                        'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                                        'date_maturity': payment.date,
                                        'partner_id': payment.partner_id.id,
                                        'account_id': payment.destination_account_id.id,
                                        'payment_id': payment.id,
                                    }),
                                    # Liquidity line.
                                    (0, 0, {
                                        'name': liquidity_line_name,
                                        'amount_currency': -liquidity_amount,
                                        'currency_id': liquidity_line_currency_id,
                                        'debit': balance < 0.0 and -balance or 0.0,
                                        'credit': balance > 0.0 and balance or 0.0,
                                        'date_maturity': payment.date,
                                        'partner_id': payment.partner_id.id,
                                        'account_id': liquidity_line_account.id,
                                        'payment_id': payment.id,
                                    }),
                                ],
                            }

                            if write_off_balance:

                                move_vals['line_ids'].append((0, 0, {
                                    'name': payment.writeoff_label,
                                    'amount_currency': -write_off_amount,
                                    'currency_id': currency_id,
                                    'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                                    'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                                    'date_maturity': payment.date,
                                    'partner_id': payment.partner_id.id,
                                    'account_id': payment.writeoff_account_id.id,
                                    'payment_id': payment.id,
                                }))

                            if move_names:
                                move_vals['name'] = move_names[0]

                            records.update({
                                str(inv_move) : [move_vals]
                                })
                        all_move_vals.append(records)
                        return all_move_vals
                    else:
                        return super(account_payment,self)._prepare_payment_moves()

        return super(account_payment,self)._prepare_payment_moves()