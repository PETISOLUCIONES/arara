from odoo import api, fields, models

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    documento_equivalente = fields.Boolean(string='Documento equivalente')
