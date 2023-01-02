# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from xml.dom.xmlbuilder import DOMInputSource
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning

import logging
_logger = logging.getLogger(__name__)

class LegalReportsAccountRows(models.Model):
    _name = 'legal.reports.account.rows'
    _order = "lra_id,id"

    name = fields.Char(string='Columna', required=True)
    lra_id = fields.Many2one(
            comodel_name='legal.reports.account', 
            ondelete='cascade', 
            required=True,
            index=True)  


class LegalReportsAccountLine(models.Model):
    _name = 'legal.reports.account.line'
    _order = "lra_id,id"

    name = fields.Many2one('legal.reports.account.rows', 
            string='Columnas',
            required=True)
    account_ids = fields.Many2many(comodel_name='account.account',     
                string='Cuenta(s)', required=True)
    balance = fields.Boolean(string='Incluir Saldo Inicial')
    operation = fields.Selection([
                ('debit_credit','Debito - Credito'),
                ('credit_debit','Credito - Debito'),
                ('debit','Debit'),
                ('credit','Credit'),
            ], required=True, string="Operación")
    lra_id = fields.Many2one(
            comodel_name='legal.reports.account', 
            ondelete='cascade', 
            required=True,
            index=True)  
    child_id = fields.Many2one(related='lra_id.parent_id', store=True)            

class LegalReportsAccount(models.Model):
    _name = 'legal.reports.account'
    _description = 'Informes Legales'

    def _compute_child_count(self):
        for rec in self:
            if rec.formats == 'format':
                rec.child_count = len(rec.child_ids)                

    name = fields.Char(
        string='Formato/Concepto',
        required=True)
    description = fields.Char(
        string=u'Descripción',
        required=True)
    parent_id = fields.Many2one(
        string='Informe relacionado', index=True,
        comodel_name='legal.reports.account', )
    parent_name = fields.Char(
        string='Nombre Padre',
        related='parent_id.name', readonly=True, )
    child_ids = fields.One2many(
        string='Informes',
        comodel_name='legal.reports.account', inverse_name='parent_id',
        domain=[('active', '=', True)])  # force "active_test" domain to bypass _search() override
    color = fields.Integer(
        string="Color",
        default=0)
    active = fields.Boolean(
        string="Activo",
        default=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.user.company_id,
        string='Compañia',
        required=True,)
    formats = fields.Selection([
        ('format', 'Formato'),
        ('concept', 'Concepto'),
    ], string='Formato')
    child_count = fields.Integer('Hijos', compute="_compute_child_count")
    report_base = fields.Float(string=u'Base (Cuantías Menores)', default=100000)
    lines_ids = fields.One2many('legal.reports.account.line', 'lra_id', string='Reportar')
    rows_ids = fields.One2many('legal.reports.account.rows', 'lra_id', string='Nombre de Columnas')
    note = fields.Text(
        string=u"Información adicional", )

    _sql_constraints = [
        ('unique_concept', 'unique (parent_id, name)', u'El concepto o formato debe ser único, intente cambiar el nombre!')
    ]

    def action_add_chils(self):
        view_form = self.env.ref('l10n_co_legal_reports.view_legal_report_account_form')
        view_tree = self.env.ref('l10n_co_legal_reports.view_legal_report_account_tree')
        return {
            'name': ('Concepto'),
            'type': 'ir.actions.act_window',
            'res_model': 'legal.reports.account',
            'view_mode': 'tree',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'context': {
                'default_parent_id': self.id,
                'default_formats': 'concept',
            },
            'domain':[('parent_id','=', self.id)],
            'target': 'current',
        }

    """"
    @api.model
    def create(self, value):
        account_domain = value.get('account_domain', False)
        if account_domain:
            account_ids = []
            try:
                aaccount_domain = list(account_domain.split(" "))
                for ad in aaccount_domain:
                    a_ids = self.env['account.account'].search([('code','=ilike', ad)])
                    if a_ids:
                        account_ids += a_ids.ids
                if account_ids:
                    account_ids = self.env['account.account'].browse(account_ids)
                    value['account_ids'] = [(6, 0, account_ids.ids)]
            except:
                raise ValidationError(_("Error en la definición del dominio"))
        else:
            raise ValidationError(_("No existe definición del dominio"))
        return super(LegalReportsAccount, self).create(value)

    @api.multi
    def write(self, value):
        account_domain = value.get('account_domain', False)
        if account_domain:
            account_ids = []
            try:
                aaccount_domain = list(account_domain.split(" "))
                for ad in aaccount_domain:
                    a_ids = self.env['account.account'].search([('code','=ilike', ad)])
                    if a_ids:
                        account_ids += a_ids.ids
                if account_ids:
                    account_ids = self.env['account.account'].browse(account_ids)
                    value['account_ids'] = [(6, 0, account_ids.ids)]
            except:
                raise ValidationError(_("Error en la definición del dominio"))
        return super(LegalReportsAccount, self).write(value)        
    """
