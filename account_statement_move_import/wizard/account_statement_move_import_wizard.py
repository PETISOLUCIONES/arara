##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AccountStatementMoveImportWizard(models.TransientModel):
    _name = "account.statement.move.import.wizard"
    _description = "account.statement.move.import.wizard"

    from_date = fields.Date(
        'From Date',
        required=True,
    )
    to_date = fields.Date(
        'To Date',
        required=True,
    )
    statement_id = fields.Many2one(
        'account.bank.statement',
        'Statement',
        default=lambda s: s.env['account.bank.statement'].browse(s._context.get('active_id', False)),
        required=True,
        ondelete='cascade',
    )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        requiered=True,
        domain=[('type', 'in', ['cash', 'bank', 'sale', 'purchase'])]
    )
    journal_account_ids = fields.Many2many(
        'account.account',
        compute='_compute_get_accounts',
        string='Journal Accounts'
    )
    move_line_ids = fields.Many2many(
        'account.move.line',
        'account_statement_import_move_line_rel',
        'line_id', 'move_line_id',
        'Journal Items',
        domain="[('journal_id', '=', journal_id), "
        "('statement_line_id', '=', False), "
        "('account_id', 'in', journal_account_ids)]"
    )

    def onchange(self, values, field_name, field_onchange):
        """Necesitamos hacer esto porque los onchange que agregan lineas,
        cuando se va a guardar el registro, terminan creando registros.
        """
        fields = []
        for field in field_onchange.keys():
            if field.startswith(('move_line_ids.')):
                fields.append(field)
        for field in fields:
            del field_onchange[field]
        return super(AccountStatementMoveImportWizard, self).onchange(
            values, field_name, field_onchange)

    @api.onchange('statement_id')
    def onchange_statement(self):
        if self.statement_id.date:
            date = self.statement_id.date
            self.from_date = date + relativedelta(day=1)
            self.to_date = date + relativedelta(day=1, months=+1, days=-1)

    @api.depends('statement_id')
    def _compute_get_journal(self):
        self.journal_id = self.statement_id.journal_id

    @api.onchange('from_date', 'to_date', 'journal_id')
    def get_move_lines(self):
        move_lines = []
        if self.journal_id.type in ['cash', 'bank']:
            if self.journal_id != self.statement_id.journal_id:
                raise UserError(_(
                    'El diario selecionado no pertenece al estracto'))
            move_lines = self.move_line_ids.search([
                ('journal_id', '=', self.journal_id.id),
                ('account_id', 'in', self.journal_account_ids.ids),
                ('statement_line_id', '=', False),
                ('date', '>=', self.from_date),
                ('date', '<=', self.to_date),
            ])
        if self.journal_id.type in ['purchase']:
            account_ids = self.env['account.account'].search([('user_type_id.type', '=', 'payable')])
            move_lines = self.move_line_ids.search([
                ('journal_id', '=', self.journal_id.id),
                ('account_id', 'in', account_ids.ids),
                ('amount_residual', '!=', 0.0),
                ('date', '>=', self.from_date),
                ('date', '<=', self.to_date),
            ])
        if self.journal_id.type in ['sale']:
            account_ids = self.env['account.account'].search([('user_type_id.type', '=', 'receivable')])
            move_lines = self.move_line_ids.search([
                ('journal_id', '=', self.journal_id.id),
                ('account_id', 'in', account_ids.ids),
                ('amount_residual', '!=', 0.0),
                ('date', '>=', self.from_date),
                ('date', '<=', self.to_date),
            ])
        self.move_line_ids = move_lines
        return {
            'type': 'ir.actions.act_window',
            'name': 'Statement Import Journal Items Wizard',
            'res_model': 'account.statement.move.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    @api.depends('journal_id')
    def _compute_get_accounts(self):
        self.journal_account_ids = (
            self.journal_id.default_account_id)

    def confirm(self):
        self.ensure_one()

        statement = self.statement_id
        statement_currency = statement.currency_id
        company_currency = statement.company_id.currency_id
        for line in self.move_line_ids:
            if self.journal_id.type in ['cash', 'bank'] and line.account_id not in self.journal_account_ids:
                raise UserError(_(
                    'Imported line account must be one of the journals '
                    'defaults, in this case %s') % (
                    ', '.join(self.journal_account_ids.mapped('name'))))

            if line.statement_line_id:
                raise UserError(_(
                    'Imported line must have "statement_line_id" == False'))

            # si el statement es en otra moneda, odoo interpreta que el amount
            # de las lineas es en esa moneda y no tendria sentido importar
            # otra moneda, ademas si uno hace un pago en otra moneda odoo
            # convierte la linea que afecta el banco a la moneda del banco
            if statement_currency != company_currency:
                if line.currency_id != statement_currency:
                    raise UserError(_(
                        'Si el diario del extracto es en otra moneda distinta '
                        'a la de la compañía, los apuntes a importar deben '
                        'tener como otra moneda esa misma moneda (%s)') % (
                            statement_currency.name))
                amount = line.amount_currency
                if self.journal_id.type in ['sale', 'purchase']:
                    amount = line.amount_residual_currency
                currency_id = False
                # amount_currency = False
            # si el estatement es en moneda de la cia, importamos por las dudas
            # currency y amount currency pero en realidad no son necesarios
            # y de hecho son invisibles por defecto
            else:
                amount = line.balance
                currency_id = line.currency_id.id
                # amount_currency = line.amount_currency

            line_vals = {
                'statement_id': statement.id,
                'date': line.date,
                'name': line.move_id.name or '/',
                'ref': line.ref,
                'amount': amount,
                'currency_id': currency_id,
                # 'amount_currency': amount_currency,
                # 'foreign_currency_id': line.currency2_id.id, No working
                'partner_id': line.partner_id.id,
                'payment_ref': line.move_name,
            }
            if self.journal_id.type in ['purchase', 'sale']:
                line_vals['amount'] = line.amount_residual
                # line_vals['amount_currency'] = line.amount_residual_currency
                line_vals['date'] = statement.date

            # create statement line
            statement_line = self.env['account.bank.statement.line'].create(
               line_vals)
            # statement_line = statement.line_ids.create(line_vals)
            if self.journal_id.type in ['cash', 'bank']:
                line.statement_line_id = statement_line.id
        return True
