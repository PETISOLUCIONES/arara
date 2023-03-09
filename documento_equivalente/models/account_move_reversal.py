from odoo import models, fields, api, _

class MoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    note_document_equivalent_concept = fields.Many2one("dian.note.document.equivalent.concept", string='Concepto Nota de ajuste')

    def _prepare_default_reversal(self, move):
        res = super(MoveReversal, self)._prepare_default_reversal(move)
        if move.documento_equivalente and move.move_type == 'in_invoice':
            res['note_document_equivalent_concept'] = self.note_document_equivalent_concept.id
        return res