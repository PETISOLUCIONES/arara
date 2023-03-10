# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import api, models, fields


class sale_order(models.Model):
    _inherit = 'sale.order'

    exceeded_amount = fields.Float('Cantidad excedida')

    state = fields.Selection([
        ('draft', 'Cotización'),
        ('sent', 'Cotización Enviada'),
        ('credit_limit', 'Límite de crédito'),
        ('sale', 'Órdenes de venta'),
        ('done', 'Locked'),
        ('cancel', 'Cancelada'),
    ], string='Estado', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(sale_order, self).onchange_partner_id()
        partner_id = self.partner_id
        if self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id

        if partner_id:
            if partner_id.credit_limit_on_hold:
                msg = "El cliente '" + partner_id.name + "' está en espera de límite de crédito."
                return {'warning':
                            {'title': 'Límite de crédito en espera', 'message': msg
                             }
                        }

    def action_sale_ok(self):
        partner_id = self.partner_id

        if self.partner_id.parent_id and not self.partner_id.check_credit:
            partner_id = self.partner_id.parent_id
        partner_ids = [partner_id.id]
        for partner in partner_id.child_ids:
            partner_ids.append(partner.id)

        if partner_id.check_credit:
            domain = [
                ('order_id.partner_id', 'in', partner_ids),
                ('order_id.state', 'in', ['sale', 'credit_limit', 'done'])]
            order_lines = self.env['sale.order.line'].search(domain)

            order = []
            to_invoice_amount = 0.0
            for line in order_lines:
                not_invoiced = line.product_uom_qty - line.qty_invoiced
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(
                    price, line.order_id.currency_id,
                    not_invoiced,
                    product=line.product_id, partner=line.order_id.partner_id)
                if line.order_id.id not in order:
                    if line.order_id.invoice_ids:
                        for inv in line.order_id.invoice_ids:
                            if inv.state == 'draft':
                                order.append(line.order_id.id)
                                break
                    else:
                        order.append(line.order_id.id)

                to_invoice_amount += taxes['total_included']

            domain = [
                ('move_id.partner_id', 'in', partner_ids),
                ('move_id.state', '=', 'draft'),
                ('sale_line_ids', '!=', False)]
            draft_invoice_lines = self.env['account.move.line'].search(domain)
            for line in draft_invoice_lines:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(
                    price, line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id, partner=line.move_id.partner_id)
                to_invoice_amount += taxes['total_included']

            # We sum from all the invoices lines that are in draft and not linked
            # to a sale order
            domain = [
                ('move_id.partner_id', 'in', partner_ids),
                ('move_id.state', '=', 'draft'),
                ('sale_line_ids', '=', False)]
            draft_invoice_lines = self.env['account.move.line'].search(domain)
            draft_invoice_lines_amount = 0.0
            invoice = []
            for line in draft_invoice_lines:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(
                    price, line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id, partner=line.move_id.partner_id)
                draft_invoice_lines_amount += taxes['total_included']
                if line.move_id.id not in invoice:
                    invoice.append(line.move_id.id)

            draft_invoice_lines_amount = "{:.2f}".format(draft_invoice_lines_amount)
            to_invoice_amount = "{:.2f}".format(to_invoice_amount)
            draft_invoice_lines_amount = float(draft_invoice_lines_amount)
            to_invoice_amount = float(to_invoice_amount)
            available_credit = partner_id.credit_limit - partner_id.credit - to_invoice_amount - draft_invoice_lines_amount

            if self.amount_total > available_credit:
                imd = self.env['ir.model.data']
                exceeded_amount = (
                                          to_invoice_amount + draft_invoice_lines_amount + partner_id.credit + self.amount_total) - partner_id.credit_limit
                exceeded_amount = "{:.2f}".format(exceeded_amount)
                exceeded_amount = float(exceeded_amount)
                vals_wiz = {
                    'partner_id': partner_id.id,
                    'sale_orders': str(len(order)) + ' Valor de la orden de venta : ' + str(to_invoice_amount),
                    'invoices': str(len(invoice)) + ' Valor del borrador de la factura : ' + str(
                        draft_invoice_lines_amount),
                    'current_sale': self.amount_total or 0.0,
                    'exceeded_amount': exceeded_amount,
                    'credit': partner_id.credit,
                    'credit_limit_on_hold': partner_id.credit_limit_on_hold,
                }
                wiz_id = self.env['customer.limit.wizard'].create(vals_wiz)
                #action = imd.xmlid_to_object('dev_customer_credit_limit.action_customer_limit_wizard')
                #form_view_id = imd.xmlid_to_res_id('dev_customer_credit_limit.view_customer_limit_wizard_form')
                action = self.env.ref('dev_customer_credit_limit.action_customer_limit_wizard')
                form_view_id = self.env.ref('dev_customer_credit_limit.view_customer_limit_wizard_form')
                return {
                    'name': action.name,
                    'help': action.help,
                    'type': action.type,
                    'views': [(form_view_id.id, 'form')],
                    'view_id': form_view_id.id,
                    'target': action.target,
                    'context': action.context,
                    'res_model': action.res_model,
                    'res_id': wiz_id.id,
                }
            else:
                self.action_confirm()
        else:
            self.action_confirm()
        return True

    def action_sale_limiteCredito_excedido(self):
        partner_id = self.partner_id

        if self.partner_id.parent_id and not self.partner_id.check_credit:
            partner_id = self.partner_id.parent_id
        partner_ids = [partner_id.id]
        for partner in partner_id.child_ids:
            partner_ids.append(partner.id)

        if partner_id.check_credit:
            domain = [
                ('order_id.partner_id', 'in', partner_ids),
                ('order_id.state', 'in', ['sale', 'credit_limit', 'done'])]
            order_lines = self.env['sale.order.line'].search(domain)

            order = []
            to_invoice_amount = 0.0
            for line in order_lines:
                not_invoiced = line.product_uom_qty - line.qty_invoiced
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(
                    price, line.order_id.currency_id,
                    not_invoiced,
                    product=line.product_id, partner=line.order_id.partner_id)
                if line.order_id.id not in order:
                    if line.order_id.invoice_ids:
                        for inv in line.order_id.invoice_ids:
                            if inv.state == 'draft':
                                order.append(line.order_id.id)
                                break
                    else:
                        order.append(line.order_id.id)

                to_invoice_amount += taxes['total_included']

            domain = [
                ('move_id.partner_id', 'in', partner_ids),
                ('move_id.state', '=', 'draft'),
                ('sale_line_ids', '!=', False)]
            draft_invoice_lines = self.env['account.move.line'].search(domain)
            for line in draft_invoice_lines:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(
                    price, line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id, partner=line.move_id.partner_id)
                to_invoice_amount += taxes['total_included']

            # We sum from all the invoices lines that are in draft and not linked
            # to a sale order
            domain = [
                ('move_id.partner_id', 'in', partner_ids),
                ('move_id.state', '=', 'draft'),
                ('sale_line_ids', '=', False)]
            draft_invoice_lines = self.env['account.move.line'].search(domain)
            draft_invoice_lines_amount = 0.0
            invoice = []
            for line in draft_invoice_lines:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(
                    price, line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id, partner=line.move_id.partner_id)
                draft_invoice_lines_amount += taxes['total_included']
                if line.move_id.id not in invoice:
                    invoice.append(line.move_id.id)

            draft_invoice_lines_amount = "{:.2f}".format(draft_invoice_lines_amount)
            to_invoice_amount = "{:.2f}".format(to_invoice_amount)
            draft_invoice_lines_amount = float(draft_invoice_lines_amount)
            to_invoice_amount = float(to_invoice_amount)
            available_credit = partner_id.credit_limit - partner_id.credit - to_invoice_amount - draft_invoice_lines_amount

            if self.amount_total > available_credit:
                imd = self.env['ir.model.data']
                exceeded_amount = (
                                          to_invoice_amount + draft_invoice_lines_amount + partner_id.credit + self.amount_total) - partner_id.credit_limit
                exceeded_amount = "{:.2f}".format(exceeded_amount)
                exceeded_amount = float(exceeded_amount)

                vals_wiz = {
                    'partner_id': partner_id.id,
                    'sale_orders': str(len(order)) + ' Valor de la orden de venta : ' + str(to_invoice_amount),
                    'invoices': str(len(invoice)) + ' Valor del borrador de la factura : ' + str(
                        draft_invoice_lines_amount),
                    'current_sale': self.amount_total or 0.0,
                    'exceeded_amount': exceeded_amount,
                    'credit': partner_id.credit,
                    'credit_limit_on_hold': partner_id.credit_limit_on_hold,
                }
                wiz_id = self.env['customer.limit.wizard'].create(vals_wiz)
                vals_wiz.update({"wiz_id": wiz_id.id})
                return vals_wiz
                

    def _make_url(self, model='sale.order'):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='http://localhost:8069')
        if base_url:
            base_url += '/web/login?db=%s&login=%s&key=%s#id=%s&model=%s' % (self._cr.dbname, '', '', self.id, model)
        return base_url

    def send_mail_approve_credit_limit(self):
        #manager_group_id = self.env['ir.model.data'].get_object_reference('dev_customer_credit_limit', 'credit_limit_config')[1]
        manager_group_id = self.env.ref('dev_customer_credit_limit.credit_limit_config').id
        browse_group = self.env['res.groups'].browse(manager_group_id)
        partner_id = self.partner_id
        if self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id

        url = self._make_url('sale.order')
        subject = self.name + '-' + 'Requiere aprobación de límite de crédito'
        for user in browse_group.users:
            partner = user.partner_id
            body = '''
                        <b>Estimado ''' " %s</b>," % (partner.name) + '''
                        <p> Una orden de venta ''' "<b><i>%s</i></b>" % self.name + '''  para el cliente ''' "<b><i>%s</i></b>" % partner_id.name + ''' requiere su aprobación de límite de crédito.</p> 
                        <p>Puede acceder a la orden de venta desde la siguiente URL <br/>
                        ''' "%s" % url + ''' </p> 
                        
                        <p><b>Saludos,</b> <br/>
                        ''' "<b><i>%s</i></b>" % self.user_id.name + ''' </p> 
                        '''

            mail_values = {
                'email_from': self.user_id.email,
                'email_to': partner.email,
                'subject': subject,
                'body_html': body,
                'state': 'outgoing',
                'message_type': 'email',
            }
            mail_id = self.env['mail.mail'].create(mail_values)
            mail_id.send(True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
