# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import api, fields, models


class customer_limit_wizard(models.TransientModel):
    _name = "customer.limit.wizard"
    _description = 'Customer Credit Limit Wizard'
    
    def set_credit_limit_state(self):
        order_id = self.env['sale.order'].browse(self._context.get('active_id'))
        order_id.state = 'credit_limit'
        order_id.exceeded_amount = self.exceeded_amount
        order_id.send_mail_approve_credit_limit()
        partner_id = self.partner_id
        if partner_id.parent_id:
            partner_id= partner_id.parent_id
        partner_id.credit_limit_on_hold = self.credit_limit_on_hold
        return True

    def set_credit_limit_state_ventas(self, id_orden1):
        order_id = self.env['sale.order'].browse(id_orden1)
        order_id.state = 'credit_limit'
        order_id.exceeded_amount = self.exceeded_amount
        order_id.send_mail_approve_credit_limit()
        partner_id = self.partner_id
        if partner_id.parent_id:
            partner_id= partner_id.parent_id
        partner_id.credit_limit_on_hold = self.credit_limit_on_hold
        return True
    
    current_sale = fields.Float('Cotización actual')
    exceeded_amount = fields.Float('Cantidad excedida')
    credit = fields.Float('Total de cuentas por cobrar')
    partner_id = fields.Many2one('res.partner',string="Cliente")
    credit_limit = fields.Float(related='partner_id.credit_limit',string="Límite de crédito")
    sale_orders = fields.Char("Órdenes de venta")
    invoices = fields.Char("Facturas")
    credit_limit_on_hold = fields.Boolean('Límite de crédito en espera')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
