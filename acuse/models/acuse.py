from odoo import api, fields, models, _


class AccountAcuse(models.Model):
    _name = 'account.acuse'
    _description = 'resgitro de acuses'

    cude = fields.Char(string='CUDE')
    fecha_evento = fields.Datetime(string='fecha evento')
    codigo_evento = fields.Char(string='Codigo')
    name = fields.Char(string='numero evento')
    move_id = fields.Many2one('account.move', string='acuse',
                              index=True, required=True, readonly=True, auto_join=True, ondelete="cascade")