from odoo import models, fields, api


class DianNoteDocumentEquivalentConcept(models.Model):
    _name = 'dian.note.document.equivalent.concept'
    _description = 'Concepto de correción para notas de ajuste'

    name = fields.Char(string='Descripcion')
    code = fields.Char(string='codigo')