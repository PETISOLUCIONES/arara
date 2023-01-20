import http.client

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import date_utils
import json

class Anticipo(models.Model):
    _name = "ap.anticipo"
    _description = "Anticipo"

    name = fields.Char("Nombre", required=True)
    cuenta_anticipo_id = fields.Many2one("account.account",string="Cuenta de anticipo",required=True,
                                         domain="[['internal_type','in',('payable','receivable')]]")
    internal_type_id = fields.Selection(related="cuenta_anticipo_id.internal_type", string="Internal Type",required=True)

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    anticipo = fields.Boolean(string="Anticipo", default=False)
    tipo_anticipo_id = fields.Many2one("ap.anticipo",string="Tipo de anticipo")
    cuenta_origen_id = fields.Many2one("account.account",string="Cuenta origen")

    @api.onchange("anticipo")
    def onchange_anticipo(self):
        if not self.anticipo:
            self.tipo_anticipo_id = False

    @api.depends('journal_id', 'partner_id', 'partner_type',
                 'is_internal_transfer', 'tipo_anticipo_id')
    def _compute_destination_account_id(self):
        for pay in self:
            if not pay.anticipo:
                super(AccountPayment, pay)._compute_destination_account_id()
            else:
                pay.destination_account_id = pay.tipo_anticipo_id.cuenta_anticipo_id

    """@api.model
    def create(self, vals_list):
        if self.anticipo:
            internal_type = self.env['ap.anticipo'].search([('id','=', vals_list['tipo_anticipo_id'])]).internal_type_id
            payment_type = vals_list['payment_type']
            if internal_type == 'payable' and payment_type == 'outbound':
                return super(AccountPayment, self).create(vals_list)
            elif internal_type == 'receivable' and payment_type == 'inbound':
                return super(AccountPayment, self).create(vals_list)
            else:
                raise UserError("El tipo de pago no corresponde a el tipo de la cuenta de destino")
        else:
            return super(AccountPayment, self).create(vals_list)"""

    """def write(self, vals_list):
        if self.anticipo:
            # internal_type
            if vals_list.get('tipo_anticipo_id'):
                internal_type = self.env['ap.anticipo'].search([('id','=', vals_list['tipo_anticipo_id'])]).internal_type_id
            else:
                internal_type = self.tipo_anticipo_id.internal_type_id
    
            # payment_type
            if vals_list.get('payment_type'):
                payment_type = vals_list['payment_type']
            else:
                payment_type = self.payment_type

            if internal_type == 'payable' and payment_type == 'outbound':
                super(AccountPayment, self).write(vals_list)
            elif internal_type == 'receivable' and payment_type == 'inbound':
                super(AccountPayment, self).write(vals_list)
            else:
                raise UserError("El tipo de pago no corresponde a el tipo de la cuenta de destino")
        else:
            super(AccountPayment, self).write(vals_list)"""

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_outstanding_credits_debits_widget = fields.Text(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_to_reconcile_info')
    invoice_payments_widget = fields.Text(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_reconciled_info')

    #Quitar validación de pagos con lineas de apuntes contables.
    # Así muestra todos los pagos
    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.user_type_id.type in
                                       ('receivable', 'payable'))

            var = self.env['account.payment'].search(
                [('anticipo', '=', True), ('amount', '!=', 0),
                 ('partner_id', '=', move.commercial_partner_id.id)]).destination_account_id.ids

            a = pay_term_lines.account_id.ids
            a += var

            domain = [
                ('account_id', 'in', a),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                ('payment_id', '!=', None),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = move.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency': move.currency_id.symbol,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'position': move.currency_id.position,
                    'digits': [69, move.currency_id.decimal_places],
                    'payment_date': fields.Date.to_string(line.date),
                })

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = json.dumps(payments_widget_vals)
            move.invoice_has_outstanding = True

    #Evento Botón "Añadir" en pagos (Cambio)
    def js_assign_outstanding_line(self, line_id):
        self.ensure_one()
        lines = self.env['account.move.line'].browse(line_id)
        #lines += self.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
        lines += self.line_ids.filtered(lambda line: not line.reconciled)
        return lines.reconcile()

    #
    def _get_reconciled_info_JSON_values(self):
        self.ensure_one()
        reconciled_vals = []
        for partial, amount, counterpart_line in self._get_reconciled_invoices_partials():
            reconciled_vals.append(self._get_reconciled_vals(partial, amount, counterpart_line))
        return reconciled_vals

    #
    def _get_reconciled_invoices_partials(self):
        ''' Helper to retrieve the details about reconciled invoices.
        :return A list of tuple (partial, amount, invoice_line).
        '''
        self.ensure_one()
        pay_term_lines = self.line_ids\
            .filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))

        invoice_partials = []

        for partial in pay_term_lines.matched_debit_ids:
            invoice_partials.append((partial, partial.credit_amount_currency, partial.debit_move_id))
        for partial in pay_term_lines.matched_credit_ids:
            invoice_partials.append((partial, partial.debit_amount_currency, partial.credit_move_id))
        return invoice_partials

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    #Operación de agregar pagos a la factura (Modificada)
    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {}

        if not self:
            return results

        # List unpaid invoices
        not_paid_invoices = self.move_id.filtered(
            lambda move: move.is_invoice(
                include_receipts=True) and move.payment_state not in (
                         'paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if line.reconciled:
                raise UserError(
                    _("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                """raise UserError(
                    _("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                    % line.account_id.display_name)"""
                continue
            if line.move_id.state != 'posted':
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(
                    _("Entries doesn't belong to the same company: %s != %s")
                    % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                """raise UserError(
                    _("Entries are not from the same account: %s != %s")
                    % (account.display_name, line.account_id.display_name))"""
                continue

        sorted_lines = self.sorted(key=lambda line: (
        line.date_maturity or line.date, line.currency_id))

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines
        involved_partials = self.env['account.partial.reconcile']
        current_lines = involved_lines
        current_partials = involved_partials
        while current_lines:
            current_partials = (
                                           current_lines.matched_debit_ids + current_lines.matched_credit_ids) - current_partials
            involved_partials += current_partials
            current_lines = (
                                        current_partials.debit_move_id + current_partials.credit_move_id) - current_lines
            involved_lines += current_lines

        # ==== Create partials ====

        partials = self.env['account.partial.reconcile'].create(
            sorted_lines._prepare_reconciliation_partials())

        # Track newly created partials.
        results['partials'] = partials
        involved_partials += partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.user_type_id.type in (
        'receivable', 'payable')
        if is_cash_basis_needed and not self._context.get(
                'move_reverse_cancel'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        if involved_lines[0].currency_id and all(
                line.currency_id == involved_lines[0].currency_id for line in
                involved_lines):
            is_full_needed = all(
                line.currency_id.is_zero(line.amount_residual_currency) for
                line in involved_lines)
        else:
            is_full_needed = all(
                line.company_currency_id.is_zero(line.amount_residual) for line
                in involved_lines)

        if is_full_needed:

            # ==== Create the exchange difference move ====

            if self._context.get('no_exchange_difference'):
                exchange_move = None
            else:
                exchange_move = involved_lines._create_exchange_difference_move()
                if exchange_move:
                    exchange_move_lines = exchange_move.line_ids.filtered(
                        lambda line: line.account_id == account)

                    # Track newly created lines.
                    involved_lines += exchange_move_lines

                    # Track newly created partials.
                    exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                             + exchange_move_lines.matched_credit_ids
                    involved_partials += exchange_diff_partials
                    results['partials'] += exchange_diff_partials

                    exchange_move._post(soft=False)

            # ==== Create the full reconcile ====

            results['full_reconcile'] = self.env[
                'account.full.reconcile'].create({
                'exchange_move_id': exchange_move and exchange_move.id,
                'partial_reconcile_ids': [(6, 0, involved_partials.ids)],
                'reconciled_line_ids': [(6, 0, involved_lines.ids)],
            })

        # Trigger action for paid invoices
        not_paid_invoices \
            .filtered(
            lambda move: move.payment_state in ('paid', 'in_payment')) \
            .action_invoice_paid()

        return results
