from odoo import api, fields, models, _
from lxml import etree
import base64
import zipfile
import os
import requests
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import xml.etree.ElementTree as ET


class Invoice(models.Model):
    _inherit = 'account.journal'

    acuse_sequence_id = fields.Many2one('ir.sequence', string='Secuencia para el acuse de facturas',
                                         help="Este campo contiene la información relacionada con "
                                              "la numeración de los acuses de las facturas recibidas.",
                                         copy=False)
    acuse_sequence_number_next = fields.Integer(string='Siguiente número de acuse',
                                                 help='El siguiente númmero de secuencia puede ser usado en el próximo '
                                                      'acuse.',
                                                 compute='_compute_acuse_seq_number_next',
                                                 inverse='_inverse_acuse_seq_number_next')

    @api.depends('refund_sequence_id.number_next_actual')
    def _compute_acuse_seq_number_next(self):
        for journal in self:
            if journal.acuse_sequence_id:
                sequence = journal.acuse_sequence_id._get_current_sequence()
                journal.acuse_sequence_number_next = sequence.number_next_actual
            else:
                journal.acuse_sequence_number_next = 1

    def _inverse_acuse_seq_number_next(self):
        for journal in self:
            if journal.acuse_sequence_id:
                sequence = journal.acuse_sequence_id._get_current_sequence()
                sequence.sudo().number_next = journal.acuse_sequence_number_next

