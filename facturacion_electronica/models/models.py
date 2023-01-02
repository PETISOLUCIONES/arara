# -*- coding: utf-8 -*-
import base64
from webbrowser import open_new, open_new_tab
from werkzeug import urls
from odoo.addons.payment import utils as payment_utils

import math
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_round, float_compare
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import xml.etree.ElementTree as ET
import os
import requests
import zipfile
from datetime import datetime, date
import re
import os
import glob
import functools
import operator
import pytz



class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    concept_debit_note_id = fields.Many2one("dian.debitnoteconcept", string="Concepto")


class MoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    concept_note_credit_id = fields.Many2one("dian.creditnoteconcept", string="Concepto")

    def _prepare_default_reversal(self, move):
        res = super(MoveReversal, self)._prepare_default_reversal(move)
        res['description_code_credit'] = self.concept_note_credit_id.id
        return res



class ConceptNoteDebit(models.Model):
    _name = 'dian.debitnoteconcept'
    _description = 'Conceptos nota debito'

    name = fields.Char(String='Descripción')
    code = fields.Char(String='Codigo')


class ConceptNoteCredit(models.Model):
    _name = 'dian.creditnoteconcept'
    _description = 'Conceptos nota credito'

    name = fields.Char(String='Descripción')
    code = fields.Char(String='Codigo')


class PaymentMethod(models.Model):
    _name = 'dian.paymentmethod'
    _description = 'Metodos de pago DIAN'

    name = fields.Char(String='Nombre')
    code = fields.Char(String='Codigo')


class FormaPago(models.Model):
    _name = 'dian.paymentmean'
    _description = 'Formas de pago DIAN'

    name = fields.Char(String='Nombre')
    code = fields.Char(String='Codigo')


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    @api.onchange('template_id')
    def onchange_template_id(self):
        # r = super(AccountInvoiceSend, self).create(vals)

        ai_id = self._context['active_ids'][0]
        account_move = self.env['account.move'].search([('id', '=', ai_id)])
        ids = []
        if account_move.invoice_status_dian == "Exitoso":
            for line in account_move:
                for lines_attachment in line.attachment_ids:
                    ids.append(lines_attachment.id)
            attach = self.env['ir.attachment']
            for lines_attach in attach.search([('res_id', '=', ai_id)]):
                if lines_attach.mimetype == 'application/zip':
                    ids.append(lines_attach.id)

            self.attachment_ids = [(6, 0, ids)]
        else:
            super(AccountInvoiceSend, self).onchange_template_id()


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_report_base_filename(self, is_ok=False):
        if self.invoice_status_dian == 'Exitoso':
            return self.mostrar_pdf()
        else:
            return super(AccountMove, self)._get_report_base_filename()

    def mostrar_pdf(self):
        return open_new_tab(self.url_pdf)

    def _default_payment_method(self):
        return self.env['dian.paymentmethod'].search([('code', '=', '1')], limit=1).id

    def _default_payment_mean(self):
        return self.env['dian.paymentmean'].search([('code', '=', '1')], limit=1).id

    payment_method_id = fields.Many2one("dian.paymentmethod", string='Método de pago', default=_default_payment_method)
    payment_mean_id = fields.Many2one('dian.paymentmean', string='Forma de pago', default=_default_payment_mean)
    description_code_credit = fields.Many2one("dian.creditnoteconcept", string='Concepto Nota de Credito')
    description_code_debit = fields.Many2one("dian.debitnoteconcept", string='Concepto Nota de Débito')
    debit_note = fields.Boolean(string='Nota débito', related='journal_id.debit_note')
    url_pdf = fields.Char(string='Representación grafica', track_visibility='onchange', copy=False)
    url_xml = fields.Char(string='Archivo XML', track_visibility='onchange', copy=False)
    invoice_status_dian = fields.Selection(selection=[('Exitoso', 'Exitoso'), ('Fallida', 'Fallida')],
                                           string='Estado de la factura DIAN', copy=False, track_visibility='onchange',
                                           readonly=True)
    description_status_dian = fields.Char(string='Descripcion del estado de la factura', copy=False,
                                          track_visibility='onchange', readonly=True)
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='attachments_rel',
        column1='account_id',
        column2='attachment_id',
        string='Archivo Adjunto',
        copy=False
    )
    comentario = fields.Char(string='Comentario')
    currency_rate = fields.Float(string='Tasa de cambio', digits=0, compute='onchange_currency_invoice')
    invoice_batch = fields.Boolean('Facturar en batch', help='Si esta opción esta marcada enviará de forma automatica la factura a la DIAN')

    def send_invoice_dian_auto(self):
        invoices = self.env['account.move'].search([('state', '=', 'posted'),
                                                    ('move_type', '=', 'out_invoice'),
                                                    ('invoice_status_dian', '!=', 'Exitoso'),
                                                    ('invoice_batch', '=', True)])
        for invoice in invoices:
            invoice.action_post1()

    @api.depends("currency_id", "invoice_date")
    def onchange_currency_invoice(self):
        for move in self:
            date = move.invoice_date
            rate = move.currency_id.with_context(date=date).rate
            move.currency_rate = 1 / rate

    def action_invoice_sent(self):
        rslt = super(AccountMove, self).action_invoice_sent()
        template = self.env.ref('facturacion_electronica.email_template_electronic_invoice', raise_if_not_found=False)
        if self.url_pdf and self.invoice_status_dian == "Exitoso":
            rslt['context']['custom_layout'] = "facturacion_electronica.mail_electronic_invoice"
            rslt['context']['default_use_template'] = bool(template)
            rslt['context']['default_template_id'] = template and template.id or False
        return rslt

    # Imprime la representación gráfica en lugar de la factura de Odoo
    def action_invoice_print(self):
        if any(not move.is_invoice(include_receipts=True) for move in self):
            raise UserError(_("Only invoices could be printed."))
        self.filtered(lambda inv: not inv.is_move_sent).write({'is_move_sent': True})
        if self.url_pdf and self.invoice_status_dian == "Exitoso":
            return {
                'type': 'ir.actions.act_url',
                'url': self.url_pdf,
                'target': 'new',
            }
        else:
            if self.user_has_groups('account.group_account_invoice'):
                return self.env.ref('account.account_invoices').report_action(self)
            else:
                return self.env.ref('account.account_invoices_without_payment').report_action(self)

    # Si la factura se encuentra aceptada por la DIAN, no permite generar la representación de Odoo
    def _get_report_base_filename(self):
        if any(not move.is_invoice() for move in self):
            raise UserError(_("Only invoices could be printed."))

        if any(move.url_pdf and move.invoice_status_dian == "Exitoso" for move in self):
            raise UserError(_("Esta factura se encuentra aceptada por la DIAN. Por favor utilice la representación gráfica."))

        return self._get_move_display_name()


    def _generate_link(self):
        for move in self:
            base_url = move.get_base_url()  # Don't generate links for the wrong website
            totales = move.obtener_totales(move)
            access_token = payment_utils.generate_access_token(
                move.partner_id.id, totales['total'], move.currency_id.id
            )
            link = f'{base_url}/payment/pay' \
                   f'?reference={urls.url_quote(move.name)}' \
                   f'&amount={totales["total"]}' \
                   f'&currency_id={move.currency_id.id}' \
                   f'&partner_id={move.partner_id.id}' \
                   f'&company_id={move.company_id.id}' \
                   f'&invoice_id={move.id}' \
                   f'{"&acquirer_id=" +  "" }' \
                   f'&access_token={access_token}'
            return link


    def create_dict_company_dian(self, move):
        FiscalResposability_c = move.GetResponsibilities(move.company_id.fiscal_responsibility_ids)
        nit_company = move.GetNitCompany(move.company_id.vat)
        datos = dict(company=nit_company,
                     StateTaxID=nit_company,
                     IdentificationType=move.company_id.document_type_id.code,
                     Name=move.company_id.name,
                     RegimeType_c=move.company_id.regime_type,
                     FiscalResposability_c=FiscalResposability_c,
                     OperationType_c=move.company_id.operation_type_id.code,
                     CompanyType_c=move.company_id.company_type_id.code,
                     State=move.company_id.state_id.name,
                     StateNum=move.company_id.state_id.dian_state_code,
                     City=move.company_id.city,
                     CityNum=move.company_id.city_id.code,
                     Address1=move.company_id.street,
                     CurrencyCode=move.company_id.currency_id.name,
                     CountryName=move.company_id.country_id.name,
                     CountryCode=move.company_id.country_id.code,
                     OrderNum=move.invoice_origin,
                     PostalZone=move.company_id.zip,
                     PhoneNum=move.company_id.phone,
                     Email=move.company_id.email,
                     WebPage=move.company_id.website,
                     CorporateRegistration=move.company_id.commercial_registration)
        return datos

    def obtener_totales(self, move):
        total_descuento = 0
        total_descuento_global = 0
        total_impuestos = 0
        total_retenciones = 0
        total_reteiva = 0
        total_reteica = 0
        subtotal = 0
        for line in move.invoice_line_ids:
            if line.display_type != 'line_section' and line.display_type != 'line_note':
                line_price_unit = move.get_price_unit_inv_line(line)
                producto_desc = self.env.ref('facturacion_electronica.product_product_condition_discount').id
                if line_price_unit > 0:
                    line_quantity = move.get_line_quantity(line)
                    total_descuento = total_descuento + ((line.discount / 100) * line_price_unit * line_quantity)

                    price_unit_wo_discount = line_price_unit * (1 - (line.discount / 100.0))
                    line_price_subtotal = line_quantity * price_unit_wo_discount

                    subtotal = subtotal + line_price_subtotal
                    for tax in line.tax_ids:
                        if tax.type_tax.name == 'IVA':
                            total_impuestos += (tax.amount / 100) * line.price_subtotal
                        elif tax.type_tax.name == 'ReteFuente':
                            total_retenciones = total_retenciones + ((tax.amount / 100) * (
                                    (line_price_unit * line_quantity) - (
                                    (line.discount / 100) * line_price_unit * line_quantity)))
                        elif tax.type_tax.name == 'ReteIVA':
                            total_reteiva = total_reteiva + ((tax.amount / 100) * (
                                    (line_price_unit * line_quantity) - (
                                    (line.discount / 100) * line_price_unit * line_quantity)))
                        elif tax.type_tax.name == 'ReteICA':
                            total_reteica = total_reteica + ((tax.amount / 100) * (
                                    (line_price_unit * line_quantity) - (
                                    (line.discount / 100) * line_price_unit * line_quantity)))
                elif line_price_unit < 0 and line.product_id.id == producto_desc:
                    total_descuento_global = total_descuento_global + (-1 * line_price_unit)

        total = subtotal + total_impuestos - total_descuento_global
        if total_descuento_global > 0 and total_descuento > 0:
            raise UserError("Solo puedes aplicar descuentos por linea o por el total de la factura")
        return {'total': total,
                'subtotal': subtotal,
                'total_impuestos': total_impuestos,
                'total_retenciones': total_retenciones,
                'total_reteiva': total_reteiva,
                'total_reteica': total_reteica,
                'total_descuento': total_descuento,
                'total_descuento_global': total_descuento_global}

    def obtener_resolucion_encabezado(self, move, invoice_type):
        if invoice_type == '91':
            return {'InvoiceRef': move.reversed_entry_id.name,
                    'InvoiceTypeRef': move.GetInvoiceType(move.reversed_entry_id),
                    'InvoiceDateRef': move.reversed_entry_id.invoice_date.strftime('%d/%m/%Y %H:%M:%S') if move.reversed_entry_id.name else "0",
                    'DueDateRef': move.reversed_entry_id.invoice_date_due.strftime('%d/%m/%Y %H:%M:%S') if move.reversed_entry_id.name else "0",
                    'CMReasonCode_c': move.description_code_credit.code,
                    'CMReasonDesc_c': move.description_code_credit.name,
                    'DMReasonCode_c': '0',
                    'DMReasonDesc_c': '0',
                    'CalculationRate_c': '0',
                    'DateCalculationRate_c': '0',
                    'Resolution_str': move.journal_id.refund_sequence_id.resolution_id.resolution_resolution,
                    'ResolutionPrefix': move.journal_id.refund_sequence_id.prefix,
                    'ResolutionDateInvoice': move.journal_id.refund_sequence_id.resolution_id.resolution_resolution_date.strftime(
                        '%Y-%m-%d'),
                    'ResolutionDateFrom': move.journal_id.refund_sequence_id.resolution_id.resolution_date_from.strftime(
                        '%Y-%m-%d'),
                    'ResolutionDateTo': move.journal_id.refund_sequence_id.resolution_id.resolution_date_to.strftime(
                        '%Y-%m-%d'),
                    'ResolutionRankFrom': str(move.journal_id.refund_sequence_id.resolution_id.resolution_from),
                    'ResolutionRankTo': str(move.journal_id.refund_sequence_id.resolution_id.resolution_to),
                    'TecnicalKey': move.journal_id.refund_sequence_id.resolution_id.resolution_technical_key}
        elif invoice_type == '92':
            return {'InvoiceRef': move.debit_origin_id.name,
                    'InvoiceTypeRef': move.GetInvoiceType(move.debit_origin_id),
                    'InvoiceDateRef': move.debit_origin_id.invoice_date.strftime('%d/%m/%Y'),
                    'DueDateRef': move.debit_origin_id.invoice_date_due.strftime('%d/%m/%Y'),
                    'CMReasonCode_c': '0',
                    'CMReasonDesc_c': '0',
                    'DMReasonCode_c': move.description_code_debit.code,
                    'DMReasonDesc_c': move.description_code_debit.name,
                    'CalculationRate_c': '0',
                    'DateCalculationRate_c': '0',
                    'Resolution_str': move.journal_id.sequence_id.resolution_id.resolution_resolution,
                    'ResolutionPrefix': move.journal_id.sequence_id.prefix,
                    'ResolutionDateInvoice': move.journal_id.sequence_id.resolution_id.resolution_resolution_date.strftime(
                        '%Y-%m-%d'),
                    'ResolutionDateFrom': move.journal_id.sequence_id.resolution_id.resolution_date_from.strftime('%Y-%m-%d'),
                    'ResolutionDateTo': move.journal_id.sequence_id.resolution_id.resolution_date_to.strftime('%Y-%m-%d'),
                    'ResolutionRankFrom': str(move.journal_id.sequence_id.resolution_id.resolution_from),
                    'ResolutionRankTo': str(move.journal_id.sequence_id.resolution_id.resolution_to),
                    'TecnicalKey': move.journal_id.sequence_id.resolution_id.resolution_technical_key}
        elif invoice_type == '02':
            inv_date = move.invoice_date
            rate = 1 / move.currency_id.with_context(date=inv_date).rate
            return {'InvoiceRef': '0',
                    'InvoiceTypeRef': '0',
                    'InvoiceDateRef': '0',
                    'DueDateRef': '0',
                    'CMReasonCode_c': '0',
                    'CMReasonDesc_c': '0',
                    'DMReasonCode_c': '0',
                    'DMReasonDesc_c': '0',
                    'CalculationRate_c': str(round(rate, 2)),
                    'DateCalculationRate_c': inv_date.strftime('%Y-%m-%d'),
                    'Resolution_str': move.journal_id.sequence_id.resolution_id.resolution_resolution,
                    'ResolutionPrefix': move.journal_id.sequence_id.prefix,
                    'ResolutionDateInvoice': move.journal_id.sequence_id.resolution_id.resolution_resolution_date.strftime(
                        '%Y-%m-%d'),
                    'ResolutionDateFrom': move.journal_id.sequence_id.resolution_id.resolution_date_from.strftime('%Y-%m-%d'),
                    'ResolutionDateTo': move.journal_id.sequence_id.resolution_id.resolution_date_to.strftime('%Y-%m-%d'),
                    'ResolutionRankFrom': str(move.journal_id.sequence_id.resolution_id.resolution_from),
                    'ResolutionRankTo': str(move.journal_id.sequence_id.resolution_id.resolution_to),
                    'TecnicalKey': move.journal_id.sequence_id.resolution_id.resolution_technical_key,}
        else:
            return {'InvoiceRef': '0',
                    'InvoiceTypeRef': '0',
                    'InvoiceDateRef': '0',
                    'DueDateRef': '0',
                    'CMReasonCode_c': '0',
                    'CMReasonDesc_c': '0',
                    'DMReasonCode_c': '0',
                    'DMReasonDesc_c': '0',
                    'CalculationRate_c': '0',
                    'DateCalculationRate_c': '0',
                    'Resolution_str': move.journal_id.sequence_id.resolution_id.resolution_resolution,
                    'ResolutionPrefix': move.journal_id.sequence_id.prefix,
                    'ResolutionDateInvoice': move.journal_id.sequence_id.resolution_id.resolution_resolution_date.strftime(
                        '%Y-%m-%d'),
                    'ResolutionDateFrom': move.journal_id.sequence_id.resolution_id.resolution_date_from.strftime('%Y-%m-%d'),
                    'ResolutionDateTo': move.journal_id.sequence_id.resolution_id.resolution_date_to.strftime('%Y-%m-%d'),
                    'ResolutionRankFrom': str(move.journal_id.sequence_id.resolution_id.resolution_from),
                    'ResolutionRankTo': str(move.journal_id.sequence_id.resolution_id.resolution_to),
                    'TecnicalKey': move.journal_id.sequence_id.resolution_id.resolution_technical_key}

    def create_dict_invoicehead_dian(self, move):
        invoicetype = move.GetInvoiceType(move)
        totales = self.obtener_totales(move)
        resolucion = self.obtener_resolucion_encabezado(move, invoicetype)
        nit_company = move.GetNitCompany(move.company_id.vat)
        CustNum = move.GetNitCompany(move.partner_id.vat)
        comment = self.cleanhtml(str(move.narration))
        # Get current timezone
        tz = self.env.user.tz
        if tz:
            local_tz = pytz.timezone(tz)
        else:
            local_tz = pytz.utc

        # Get current time
        now = datetime.now(local_tz)
        # Delivery info
        direccion = move.partner_shipping_id
        datos = dict(Company=nit_company,
                     InvoiceType=invoicetype,
                     InvoiceNum=move.name,
                     LegalNumber=move.name,
                     InvoiceRef=resolucion['InvoiceRef'],
                     InvoiceTypeRef=resolucion['InvoiceTypeRef'],
                     InvoiceDateRef=resolucion['InvoiceDateRef'],
                     DueDateRef=resolucion['DueDateRef'],
                     CMReasonCode_c=resolucion['CMReasonCode_c'],
                     CMReasonDesc_c=resolucion['CMReasonDesc_c'],
                     DMReasonCode_c=resolucion['DMReasonCode_c'],
                     DMReasonDesc_c=resolucion['DMReasonDesc_c'],
                     CustNum=CustNum,
                     ContactName=direccion.name if direccion else move.partner_id.name,
                     ContactCountry=direccion.country_id.name if direccion else move.partner_id.country_id.name,
                     ContactState=direccion.state_id.name if direccion else move.partner_id.state_id.name,
                     ContactCity=direccion.city_id.name if direccion else move.partner_id.city_id.name,
                     ContactAddress=direccion.street if direccion else move.partner_id.street,
                     CustomerName=move.partner_id.name,
                     InvoiceDate=now.strftime('%d/%m/%Y %H:%M:%S'),
                     DueDate=move.invoice_date_due.strftime('%d/%m/%Y')+ " " + now.strftime('%H:%M:%S'), #now.strftime('%d/%m/%Y %H:%M:%S'),
                     DocWHTaxAmt=str(round(abs(totales['total_retenciones']), 2)),
                     TaxAmtLineReteiva=str(round(abs(totales['total_reteiva']), 2)),
                     TaxAmtLineReteica=str(round(abs(totales['total_reteica']), 2)),
                     InvoiceComment=comment if comment else ' ',
                     InvoiceComment1=str(move.currency_rate),
                     InvoiceComment2=move.invoice_user_id.name,
                     InvoiceComment3=str(move.comentario) if move.comentario else "",
                     InvoiceComment4=resolucion['CMReasonDesc_c'] if invoicetype == '91' else resolucion['DMReasonDesc_c'] if invoicetype == '92' else "",
                     CurrencyCode=move.currency_id.name,
                     CurrencyCodeCurrencyID=move.currency_id.name,
                     ContingencyInvoice='0',
                     NetWeight='0',
                     PorcAdministracion='0',
                     PorcImprevistos='0',
                     PorcUtilidad='0',
                     GrossWeight='0',
                     NumberBoxes='0',
                     PONum='0',
                     Remission='0',
                     Resolution=resolucion['Resolution_str'],
                     ResolutionPrefix=resolucion['ResolutionPrefix'],
                     ResolutionDateInvoice=resolucion['ResolutionDateInvoice'],
                     ResolutionDateFrom=resolucion['ResolutionDateFrom'],
                     ResolutionDateTo=resolucion['ResolutionDateTo'],
                     ResolutionRankFrom=resolucion['ResolutionRankFrom'],
                     ResolutionRankTo=resolucion['ResolutionRankTo'],
                     TecnicalKey=resolucion['TecnicalKey'],
                     IdSoftware=move.company_id.software_id,
                     TestSet=move.company_id.test_set,
                     PinSoftware=move.company_id.software_pin,
                     InvoicePeriod='0',
                     PaymentMeansID_c=move.payment_mean_id.code,
                     PaymentMeansDescription=move.payment_mean_id.name,
                     PaymentMeansCode_c=move.payment_method_id.code,
                     PaymentDurationMeasure=str(abs((move.invoice_date_due - move.invoice_date).days)),
                     PaymentDueDate=move.invoice_date_due.strftime('%Y-%m-%d'),
                     CalculationRate_c=resolucion['CalculationRate_c'],
                     DateCalculationRate_c=resolucion['DateCalculationRate_c'],
                     ConditionPay=move.invoice_payment_term_id.name if move.invoice_payment_term_id else ' ',
                     DspDocSubTotal=str(round(float_round(totales['subtotal'], precision_digits=2), 2)),
                     DocTaxAmt=str(round(float_round(totales['total_impuestos'], precision_digits=2),2)),
                     DspDocInvoiceAmt=str(round(float_round(totales['total'], precision_digits=2), 2)),
                     Discount=str(round(float_round(totales['total_descuento'], precision_digits=2), 2)),
                     GlobalDiscount=str(round(float_round(totales['total_descuento_global'], precision_digits=2), 2)))
        return datos

    def get_price_unit_inv_line(self, line):
        line_quantity = self.get_line_quantity(line)
        line_price_unit = float_round((line.price_subtotal / (1 - (line.discount / 100))) / line_quantity,
                                      precision_rounding=line.move_id.currency_id.rounding)
        return line_price_unit

    def get_line_quantity(self, line):
        line_quantity = line.quantity
        return line_quantity

    def create_lineas_inv_tax(self, move, producto_regalo):
        datos = []
        impuestosFactura = []
        InvoiceNum = move.name
        nit_company = move.GetNitCompany(move.company_id.vat)
        CurrencyCode = move.currency_id.name
        i = 1
        for line in move.invoice_line_ids:
            if line.display_type != 'line_section' and line.display_type != 'line_note':
                line_price_unit = move.get_price_unit_inv_line(line)
                line_quantity = move.get_line_quantity(line)
                price_unit_wo_discount = line_price_unit * (1 - (line.discount / 100.0))
                line_price_subtotal = (round(line_price_unit, 2) * line_quantity * (1-(line.discount/100)))
                if line_price_subtotal > 0 and line.name not in producto_regalo:
                    if len(line.tax_ids) == 0:
                        dato = dict(Company=nit_company,
                                    InvoiceNum=InvoiceNum,
                                    InvoiceLine=str(i),
                                    CurrencyCode=CurrencyCode,
                                    RateCode="IVA",
                                    DocTaxableAmt=str(round(line_price_subtotal, 2)),
                                    TaxAmt="0",
                                    DocTaxAmt="0",
                                    Percent="0",
                                    WithholdingTax_c="False")
                        datos.append(dato)
                    else:
                        for tax in line.tax_ids:
                            impuestosFactura.append(tax.type_tax.name)
                            dato = dict(Company=nit_company,
                                        InvoiceNum=InvoiceNum,
                                        InvoiceLine=str(i),
                                        CurrencyCode=CurrencyCode,
                                        RateCode=tax.type_tax.name,
                                        DocTaxableAmt=str(round(line_price_subtotal, 2)),
                                        TaxAmt=str(abs(round(
                                            float_round(line_price_subtotal * tax.amount / 100, precision_digits=2),
                                            2))),
                                        DocTaxAmt=str(abs(round(
                                            float_round(line_price_subtotal * tax.amount / 100, precision_digits=2),
                                            2))),
                                        Percent=(str("{0:.2f}".format(abs(tax.amount)))),
                                        WithholdingTax_c=str(tax.type_tax.retention))
                            datos.append(dato)
                i = i + 1
        return {'datos': datos, 'impuestosFactura': impuestosFactura}

    def create_lineas_invc_misc(self, move, producto_regalo):
        datos = []
        InvoiceNum = move.name
        nit_company = move.GetNitCompany(move.company_id.vat)
        totales = self.obtener_totales(move)
        i = 1
        for line in move.invoice_line_ids:
            if line.display_type != 'line_section' and line.display_type != 'line_note':
                line_price_unit = move.get_price_unit_inv_line(line)
                line_quantity = move.get_line_quantity(line)
                producto_desc = self.env.ref('facturacion_electronica.product_product_condition_discount').id
                if line_price_unit > 0:
                    dato = dict(Company=nit_company,
                                InvoiceNum=InvoiceNum,
                                InvoiceLine=str(i),
                                MiscCode='0',
                                Description='Descuento',
                                MiscAmt=str(round(line_quantity * line_price_unit * (line.discount / 100), 2)),
                                DocMiscAmt='0',
                                MiscCodeDescription='Descuento',
                                PercentAmt=str(line.discount),
                                MiscType='1', )
                elif line_price_unit < 0 and line.product_id.id == producto_desc:
                    percent_discount = round(abs(line_price_unit) * 100 / totales['subtotal'], 2)
                    dato = dict(Company=nit_company,
                                InvoiceNum=InvoiceNum,
                                InvoiceLine="0",
                                MiscCode='01',
                                Description='Descuento Condicionado',
                                MiscAmt=str(abs(line_price_unit)),
                                DocMiscAmt='0',
                                MiscCodeDescription='Descuento Condicionado',
                                PercentAmt=str(percent_discount),
                                MiscType='1', )
                else:
                    pos = 0
                    totalLinea = 0
                    descuento = line_quantity * line_price_unit
                    for move in self:
                        indice = 1
                        if pos > 0:
                            break
                        for line in move.invoice_line_ids:
                            if line.display_type != 'line_section' and line.display_type != 'line_note':
                                if line.name in producto_regalo:
                                    # totalLinea = line.quantity * line.price_unit
                                    totalLinea = line_quantity * line_price_unit
                                    pos = indice
                                    break
                                indice = indice + 1

                    if totalLinea == 0:
                        pos = 0
                        totalLinea = 1

                    dato = dict(Company=nit_company,
                                InvoiceNum=InvoiceNum,
                                InvoiceLine=str(pos),
                                MiscCode='0',
                                Description='Descuento',
                                MiscAmt=str(round(-1 * descuento, 2)),
                                DocMiscAmt='0',
                                MiscCodeDescription='Descuento',
                                PercentAmt=str(((-1 * descuento) * 100) / totalLinea),
                                MiscType='1', )
                datos.append(dato)
                i = i + 1
        return {'datos': datos}

    def create_dict_sales_rtc(self, move, impuestosFactura):
        nit_company = move.GetNitCompany(move.company_id.vat)
        datos = [dict(Company=nit_company,
                      RateCode='IVA',
                      TaxCode='IVA',
                      Description='Impuesto de Valor Agregado',
                      IdImpDIAN_c='01',
                      ),
                 ]
        if 'ReteFuente' in impuestosFactura:
            datos.append(
                dict(Company=nit_company,
                     RateCode='ReteFuente',
                     TaxCode='ReteFuente',
                     Description='Retención sobre Renta',
                     IdImpDIAN_c='06',
                     ),
            )

        if 'ReteICA' in impuestosFactura:
            datos.append(
                dict(Company=nit_company,
                     RateCode='ReteICA',
                     TaxCode='ReteICA',
                     Description='Retención sobre el ICA',
                     IdImpDIAN_c='07',
                     ),
            )

        if 'ReteIVA' in impuestosFactura:
            datos.append(
                dict(Company=nit_company,
                     RateCode='ReteIVA',
                     TaxCode='ReteIVA',
                     Description='Retención sobre el IVA',
                     IdImpDIAN_c='05',
                     ),
            )

        if 'AIU' in impuestosFactura:
            datos.append(
                dict(Company=nit_company,
                     RateCode='AIU',
                     TaxCode='AIU',
                     Description='Otros tributos, tasas, contribuciones, y similares',
                     IdImpDIAN_c='ZZ',
                     ),
            )
        return datos

    def create_dict_customer(self, move):
        nit_company = move.GetNitCompany(move.company_id.vat)
        CustNum = move.GetNitCompany(move.partner_id.vat)
        CustID = move.TypeDocumentCust(move.partner_id.l10n_latam_identification_type_id.l10n_co_document_code)
        FiscalResposability_partner = self.GetResponsibilities(move.partner_id.fiscal_responsibility_partner_ids)
        datos = dict(Company=nit_company,
                     CustID=CustID,
                     CustNum=CustNum,
                     ResaleID=CustNum,
                     Name=move.partner_id.name,
                     Address1=move.partner_id.street,
                     EMailAddress=move.partner_id.email,
                     PhoneNum=move.partner_id.phone,
                     CurrencyCode=move.currency_id.name,
                     Country=move.partner_id.country_id.name,
                     CountryCode=move.partner_id.country_id.code,
                     PostalZone=move.partner_id.zip,
                     RegimeType_c=move.partner_id.organization_type_id.code,
                     FiscalResposability_c=FiscalResposability_partner,
                     State=move.partner_id.state_id.name,
                     StateNum=move.partner_id.state_id.dian_state_code,
                     City=move.partner_id.city_id.name,
                     CityNum=move.partner_id.city_id.code,
                     CorporateRegistration=move.partner_id.commercial_registration_partner)
        return datos

    def create_dict_onetime(self, move):
        nit_company = move.GetNitCompany(move.company_id.vat)
        CustNum = move.GetNitCompany(move.partner_id.vat)
        CustID = move.TypeDocumentCust(move.partner_id.l10n_latam_identification_type_id.l10n_co_document_code)
        datos = dict(Company=nit_company,
                     IdentificationType=CustID,
                     COOneTimeID=CustNum,
                     CompanyName=move.partner_id.name,
                     CountryName=move.partner_id.country_id.name,
                     CountryCode=move.partner_id.country_id.code, )
        return datos

    def get_dict_lineas_fact(self, move):
        datos = []
        producto_regalo = []
        InvoiceNum = move.name
        CurrencyCode = move.currency_id.name
        i = 1
        for line in move.invoice_line_ids:
            if line.display_type != 'line_section' and line.display_type != 'line_note':
                line_price_unit = move.get_price_unit_inv_line(line)
                line_quantity = move.get_line_quantity(line)
                producto_desc = self.env.ref('facturacion_electronica.product_product_condition_discount').id
                if line_price_unit > 0 and line.product_id.id != producto_desc:
                    dato = dict(InvoiceNum=InvoiceNum,
                                InvoiceLine=str(i),
                                PartNum=line.product_id.default_code,
                                LineDesc=line.name,
                                Product=line.product_id.name,
                                PartNumPartDescription=line.name,
                                SellingShipQty=str(line_quantity),
                                SalesUM=line.product_uom_id.name,

                                UnitPrice=str(round(line_price_unit, 2)),
                                DocUnitPrice=str(round(line_price_unit, 2)),
                                DocExtPrice=str(round(line_price_unit * line_quantity, 2)),
                                DspDocExtPrice=str(round(line_price_unit * line_quantity, 2)),
                                DiscountPercent=str(line.discount),
                                Discount=str(round(line_price_unit * line_quantity * (line.discount / 100), 2)),
                                DocDiscount='0',
                                DspDocLessDiscount=str(
                                    round(line_price_unit * line_quantity * (line.discount / 100), 2)),
                                DspDocTotalMiscChrg='0',
                                CurrencyCode=CurrencyCode,
                                LineComment=line.product_id.categ_id.name,
                                LineComment1='',
                                LineComment2='',)
                    datos.append(dato)
                    i = i + 1
                else:
                    producto_regalo.append(line.name)

        return {'datos': datos, 'producto_regalo': producto_regalo}

    def get_nombreplantilla(self, move):
        tipo = move.GetInvoiceType(move)
        if tipo in ['01', '02', '91', '92']:
            return 'plantilla.xml'

    def get_url_ws(self, invoicetype, move):
        ip_ws = str(move.company_id.ip_webservice)
        url = ''
        if invoicetype == '01':
            url = 'http://' + ip_ws + '/api/EnvioFactura'
        elif invoicetype == '02':
            url = 'http://' + ip_ws + '/api/EnvioFacturaExportacion'
        elif invoicetype == '91':
            url = 'http://' + ip_ws + '/api/EnvioNotaCredito'
        else:
            url = 'http://' + ip_ws + '/api/EnvioNotaDebito'
        return url

    def action_post1(self):
        for move in self:
            file = move.get_nombreplantilla(move)
            if move.env.company.ruta_plantilla:
                ruta_plantilla = move.env.company.ruta_plantilla + '/' + file
            else:
                ruta_plantilla = file
            full_file = os.path.abspath(os.path.join('', ruta_plantilla))
            try:
                doc_xml = ET.parse(full_file)
            except:
                raise UserError("No se encontró la plantilla en la ruta " + full_file)

            root = doc_xml.getroot()

            '''DATOS EMPRESA'''
            empresa = move.create_dict_company_dian(move)
            move.EditaCompany(empresa, root)

            '''ENCABEZADO FACTURA'''
            encabezado = move.create_dict_invoicehead_dian(move)
            move.EditaNodos('InvcHead', encabezado, root)

            '''LINEAS FACTURAS'''
            lineas_factura = move.get_dict_lineas_fact(move)
            datos = lineas_factura['datos']
            producto_regalo = lineas_factura['producto_regalo']
            move.GenerarLineasFact(datos, root)

            '''IMPUESTOS'''
            impuestos = move.create_lineas_inv_tax(move, producto_regalo)
            lineas_impuestos = impuestos['datos']
            impuestosFactura = impuestos['impuestosFactura']
            move.GenerarLineasInvcTaxs(lineas_impuestos, root)

            '''DESCUENTOS'''
            descuentos = move.create_lineas_invc_misc(move, producto_regalo)
            move.GenerarLineasInvcMisc(descuentos['datos'], root)

            '''CLIENTE'''
            cliente = move.create_dict_customer(move)
            move.EditaNodos('Customer', cliente, root)

            '''SALES TRC'''
            sales_trc = move.create_dict_sales_rtc(move, impuestosFactura)
            move.GenerarLineasSalesTRCs(sales_trc, 'SalesTRC', root)

            '''COONETIME'''
            co_one_time = move.create_dict_onetime(move)
            move.EditaNodos('COOneTime', co_one_time, root)

            nit_company = move.GetNitCompany(move.company_id.vat)
            invoicetype = move.GetInvoiceType(move)
            directorio = "Facturacion/ArchivosXML/" + nit_company + "/"
            directoriozip = "Facturacion/Zip/" + nit_company + "/"
            files = glob.glob(directoriozip + '*')
            for f in files:
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"Error:{e.strerror}")

            if move.env.company.ruta_plantilla:
                ruta_xml = move.env.company.ruta_plantilla + "/ArchivosXML/" + nit_company + "/"
                directoriozip = move.env.company.ruta_plantilla + "/Zip/" + nit_company + "/"
            else:
                ruta_xml = directorio
                directoriozip = directoriozip

            try:
                os.stat(ruta_xml)
                os.stat(directoriozip)
            except:
                os.makedirs(ruta_xml)
                os.makedirs(directoriozip)

            new_file = ruta_xml + move.name.replace('/', '_') + '.xml'

            doc_xml.write(new_file)

            ip_ws = str(move.company_id.ip_webservice)
            url = move.get_url_ws(invoicetype, move)
            """if invoicetype == '01':
                url = 'http://' + ip_ws + '/api/EnvioFactura'
            elif invoicetype == '02':
                url = 'http://' + ip_ws + '/api/EnvioFacturaExportacion'
            elif invoicetype == '91':
                url = 'http://' + ip_ws + '/api/EnvioNotaCredito'
            else:
                url = 'http://' + ip_ws + '/api/EnvioNotaDebito'"""

            headers = {'content-type': 'text/xml;charset=utf-8'}

            body = open(new_file, "r").read()

            responsews = requests.post(url, data=body.encode('utf-8'), headers=headers)

            tipodato = type(responsews)
            resultados = ""
            attach = ""
            respuestaws = ""
            if responsews.status_code == 200:
                respuesta = eval(responsews.content.decode('utf-8'))
                if 'Respuesta' in respuesta:
                    resultados = respuesta['Respuesta']
                    attach = move.GetAttach(resultados)
                    respuestaws = move.GetResponseWS(resultados)

                estado_factura = ''
                if respuestaws == 'PROCESADO_CORRECTAMENTE':
                    estado_factura = 'Exitoso'

                    url_xml = 'http://' + ip_ws + '/AttachedDocuments/' + str(
                        nit_company) + '/' + attach
                    url_pdf = 'http://' + ip_ws + '/facturaPDF/' + str(
                        nit_company) + '/' + move.name + '.pdf'

                    my_xml = requests.get(url_xml).content
                    my_pdf = requests.get(url_pdf).content

                    open(directoriozip + attach, 'wb').write(my_xml)
                    open(directoriozip + move.name + '.pdf', 'wb').write(my_pdf)
                    try:
                        import zlib
                        compression = zipfile.ZIP_DEFLATED
                    except:
                        compression = zipfile.ZIP_STORED

                    zf = zipfile.ZipFile(directoriozip + attach[0:len(attach) - 4].replace('ad', 'z') + '.zip', mode='w')
                    try:
                        zf.write(directoriozip + attach, compress_type=compression,
                                 arcname=os.path.basename(directoriozip + attach))
                        zf.write(directoriozip + move.name + '.pdf', compress_type=compression,
                                 arcname=os.path.basename(directoriozip + move.name + '.pdf'))
                    finally:
                        zf.close()
                    name_zip = attach[0:len(attach) - 4].replace('ad', 'z')
                    file_zip = directoriozip + name_zip + '.zip'
                    my_zip = open(file_zip, 'rb').read()

                else:
                    estado_factura = 'Fallida'

                if estado_factura == 'Exitoso':
                    return (move.env['ir.attachment'].create({
                        'name': attach[0:len(attach) - 4].replace('ad', 'z') + ".zip",
                        'type': 'binary',
                        'res_id': move.id,
                        'res_model': 'account.move',
                        'datas': base64.b64encode(my_zip),
                        'mimetype': 'application/zip'
                    }), move.write({
                        'url_pdf': url_pdf,
                        'url_xml': url_xml,
                        'description_status_dian': respuestaws,
                        'invoice_status_dian': estado_factura
                    }))
                else:
                    if respuestaws == 'Factura ya aprobada':
                        url_xml = 'http://' + ip_ws + '/AttachedDocuments/' + str(
                            nit_company) + '/' + attach + '.xml'
                        url_pdf = 'http://' + ip_ws + '/facturaPDF/' + str(
                            nit_company) + '/' + move.name + '.pdf'

                        my_xml = requests.get(url_xml).content
                        my_pdf = requests.get(url_pdf).content

                        open(directoriozip + attach, 'wb').write(my_xml)
                        open(directoriozip + move.name + '.pdf', 'wb').write(my_pdf)
                        try:
                            import zlib
                            compression = zipfile.ZIP_DEFLATED
                        except:
                            compression = zipfile.ZIP_STORED

                        zf = zipfile.ZipFile(directoriozip + attach[0:len(attach) - 4].replace('ad', 'z') + '.zip', mode='w')
                        try:
                            zf.write(directoriozip + attach, compress_type=compression,
                                     arcname=os.path.basename(directoriozip + attach))
                            zf.write(directoriozip + move.name + '.pdf', compress_type=compression,
                                     arcname=os.path.basename(directoriozip + move.name + '.pdf'))
                        finally:
                            zf.close()
                        name_zip = attach[0:len(attach) - 4].replace('ad', 'z')
                        file_zip = directoriozip + name_zip + '.zip'
                        my_zip = open(file_zip, 'rb').read()

                        return (move.env['ir.attachment'].create({
                            'name': attach[0:len(attach) - 4].replace('ad', 'z') + ".zip",
                            'type': 'binary',
                            'res_id': move.id,
                            'res_model': 'account.move',
                            'datas': base64.b64encode(my_zip),
                            'mimetype': 'application/zip'
                        }), move.write({
                            'url_pdf': url_pdf,
                            'url_xml': url_xml,
                            'description_status_dian': 'PROCESADO_CORRECTAMENTE',
                            'invoice_status_dian': 'Exitoso'
                        }))
                    else:
                        return (move.write({
                            'description_status_dian': respuestaws,
                            'invoice_status_dian': estado_factura
                        }))
            elif responsews.status_code == 500:
                raise UserError("Error en la conexión al Web service")

    def cleanhtml(self, raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    def _get_ipwebservice(self):
        ip_ws = self.env['res.company'].search().filtered('ip_webservice')
        return ip_ws

    def EditaCompany(self, datos, root):
        nodos = root.findall("./Company/")
        for node in nodos:
            tag = node.tag
            if tag in datos:
                node.text = datos[tag]
            else:
                node.text = ''

    def EditaNodos(self, rama, datos, root):
        nodos = root.findall('.//' + rama + '/')
        # print(nodos)
        for node in nodos:
            tag = node.tag
            # print(tag)
            if tag in datos:
                node.text = datos[tag]
            else:
                node.text = ''

    def GenerarLineasFact(self, datos, root):
        node_root = root.find('./InvcDtls')
        if len(datos) > 0:
            if len(datos) > 1:
                i = 2
                longitud = len(datos)
                for x in range(longitud - 1):
                    InvcDtl = ET.Element('InvcDtl')
                    InvcDtl.attrib['id'] = str(i)
                    node_root.append(InvcDtl)
                    InvoiceNum = ET.SubElement(InvcDtl, 'InvoiceNum')
                    InvoiceLine = ET.SubElement(InvcDtl, 'InvoiceLine')
                    PartNum = ET.SubElement(InvcDtl, 'PartNum')
                    LineDesc = ET.SubElement(InvcDtl, 'LineDesc')
                    Product = ET.SubElement(InvcDtl, 'Product')
                    PartNumPartDescription = ET.SubElement(InvcDtl, 'PartNumPartDescription')
                    SellingShipQty = ET.SubElement(InvcDtl, 'SellingShipQty')
                    SalesUM = ET.SubElement(InvcDtl, 'SalesUM')
                    UnitPrice = ET.SubElement(InvcDtl, 'UnitPrice')
                    DocUnitPrice = ET.SubElement(InvcDtl, 'DocUnitPrice')
                    DocExtPrice = ET.SubElement(InvcDtl, 'DocExtPrice')
                    DspDocExtPrice = ET.SubElement(InvcDtl, 'DspDocExtPrice')
                    DiscountPercent = ET.SubElement(InvcDtl, 'DiscountPercent')
                    Discount = ET.SubElement(InvcDtl, 'Discount')
                    DocDiscount = ET.SubElement(InvcDtl, 'DocDiscount')
                    DspDocLessDiscount = ET.SubElement(InvcDtl, 'DspDocLessDiscount')
                    DspDocTotalMiscChrg = ET.SubElement(InvcDtl, 'DspDocTotalMiscChrg')
                    CurrencyCode = ET.SubElement(InvcDtl, 'CurrencyCode')
                    LineComment = ET.SubElement(InvcDtl, 'LineComment')
                    LineComment1 = ET.SubElement(InvcDtl, 'LineComment1')
                    LineComment2 = ET.SubElement(InvcDtl, 'LineComment2')
                    i += 1

            detalles = root.findall('./InvcDtls/')
            i = 0
            for detalle in detalles:
                for node in detalle:
                    tag = node.tag
                    dic = datos[i]
                    if tag in dic:
                        node.text = dic[tag]
                    else:
                        node.text = ''
                i += 1

    def GenerarLineasInvcTaxs(self, datos, root):
        node_root = root.find('./InvcTaxs')
        if len(datos) > 0:
            if len(datos) > 1:
                i = 2
                longitud = len(datos)
                for x in range(longitud - 1):
                    InvcTax = ET.Element('InvcTax')
                    InvcTax.attrib['id'] = str(i)
                    node_root.append(InvcTax)
                    Company = ET.SubElement(InvcTax, 'Company')
                    InvoiceNum = ET.SubElement(InvcTax, 'InvoiceNum')
                    InvoiceLine = ET.SubElement(InvcTax, 'InvoiceLine')
                    CurrencyCode = ET.SubElement(InvcTax, 'CurrencyCode')
                    RateCode = ET.SubElement(InvcTax, 'RateCode')
                    DocTaxableAmt = ET.SubElement(InvcTax, 'DocTaxableAmt')
                    TaxAmt = ET.SubElement(InvcTax, 'TaxAmt')
                    DocTaxAmt = ET.SubElement(InvcTax, 'DocTaxAmt')
                    Percent = ET.SubElement(InvcTax, 'Percent')
                    WithholdingTax_c = ET.SubElement(InvcTax, 'WithholdingTax_c')
                    i += 1

            detalles = root.findall('./InvcTaxs/')
            i = 0
            for detalle in detalles:
                for node in detalle:
                    tag = node.tag
                    dic = datos[i]
                    if tag in dic:
                        node.text = dic[tag]
                    else:
                        node.text = ''
                i += 1

    def GenerarLineasInvcMisc(self, datos, root):
        node_root = root.find('./InvcMiscs')
        if len(datos) > 0:
            if len(datos) > 1:
                i = 2
                longitud = len(datos)
                for x in range(longitud - 1):
                    InvcMisc = ET.Element('InvcMisc')
                    InvcMisc.attrib['id'] = str(i)
                    node_root.append(InvcMisc)
                    Company = ET.SubElement(InvcMisc, 'Company')
                    InvoiceNum = ET.SubElement(InvcMisc, 'InvoiceNum')
                    InvoiceLine = ET.SubElement(InvcMisc, 'InvoiceLine')
                    MiscCode = ET.SubElement(InvcMisc, 'MiscCode')
                    Description = ET.SubElement(InvcMisc, 'Description')
                    MiscAmt = ET.SubElement(InvcMisc, 'MiscAmt')
                    DocMiscAmt = ET.SubElement(InvcMisc, 'DocMiscAmt')
                    MiscCodeDescription = ET.SubElement(InvcMisc, 'MiscCodeDescription')
                    PercentAmt = ET.SubElement(InvcMisc, 'PercentAmt')
                    MiscType = ET.SubElement(InvcMisc, 'MiscType')
                    i += 1

            detalles = root.findall('./InvcMiscs/')
            i = 0
            for detalle in detalles:
                for node in detalle:
                    tag = node.tag
                    dic = datos[i]
                    if tag in dic:
                        node.text = dic[tag]
                    else:
                        node.text = ''
                i += 1

    def GenerarLineasSalesTRCs(self, datos, rama, root):
        node_root = root.find('./' + rama + 's')
        if len(datos) > 0:
            if len(datos) > 1:
                i = 2
                longitud = len(datos)
                for x in range(longitud - 1):
                    SalesTRC = ET.Element('SalesTRC')
                    SalesTRC.attrib['id'] = str(i)
                    node_root.append(SalesTRC)
                    Company = ET.SubElement(SalesTRC, 'Company')
                    RateCode = ET.SubElement(SalesTRC, 'RateCode')
                    TaxCode = ET.SubElement(SalesTRC, 'TaxCode')
                    Description = ET.SubElement(SalesTRC, 'Description')
                    IdImpDIAN_c = ET.SubElement(SalesTRC, 'IdImpDIAN_c')
                    i += 1

            detalles = root.findall('./' + rama + 's/')
            i = 0
            for detalle in detalles:
                for node in detalle:
                    tag = node.tag
                    dic = datos[i]
                    if tag in dic:
                        node.text = dic[tag]
                    else:
                        node.text = ''
                i += 1

    # Obtener una cadena con las responsabilidades fiscales de la empresa o del cliente
    def GetResponsibilities(self, datos):
        i = 0
        FiscalResposability = ''
        for responsability in datos:
            if i == len(datos) - 1:
                FiscalResposability = FiscalResposability + responsability.name
            else:
                FiscalResposability = FiscalResposability + responsability.name + ';'
            i += 1

        return FiscalResposability

    def GetInvoiceType(self, datos):
        invoicetype = ''
        for dato in datos:
            if dato.move_type == 'out_refund' and dato.debit_note == False:
                # invoicetype = '91'
                invoicetype = dato.journal_id.refund_sequence_id.resolution_id.document_type
            elif dato.move_type != 'out_refund' and dato.debit_note == True:
                # invoicetype = '92'
                invoicetype = dato.journal_id.sequence_id.resolution_id.document_type
            elif dato.move_type == 'out_invoice' and dato.debit_note == False:
                # invoicetype = dato.document_type
                invoicetype = dato.journal_id.sequence_id.resolution_id.document_type
            return invoicetype

    def GetType(self, invoice):
        result = ''
        if invoice == '01' or invoice == '02':
            result = 'ad'
        elif invoice == '91':
            result = 'nc'
        elif invoice == '92':
            result = 'nd'
        return

    def GetNitCompany(self, number):
        document = ''
        try:
            if '-' in number:
                document = number[0:number.find('-')]
            else:
                document = number
            return document.replace('.', '')
        except:
            return document.replace('.', '')

    def TypeDocumentCust(self, typedocument):
        type = ''
        if typedocument == 'rut':
            type = '31'
        elif typedocument == 'id_document':
            type = '13'
        elif typedocument == 'id_card':
            type = '12'
        elif typedocument == 'passport':
            type = '41'
        elif typedocument == 'foreign_id_card':
            type = '22'
        elif typedocument == 'external_id':
            type = '50'
        elif typedocument == 'diplomatic_card':
            type = ''
        elif typedocument == 'residence_document':
            type = ''
        elif typedocument == 'civil_registration':
            type = '11'
        elif typedocument == 'national_citizen_id':
            type = '13'
        elif typedocument == 'niup_id':
            type = '91'
        return type

    def GetResponseWS(self, response):
        respuesta = ''
        if ';nombreattach:' in response:
            respuesta = response[0:response.find(';nombreattach:')]
        else:
            respuesta = response
        return respuesta

    def GetAttach(self, response):
        respuesta = ''
        if ';nombreattach:' in response:
            respuesta = response[response.find(';nombreattach:') + 14:len(response)]
        return respuesta

    def post(self):
        res = super(AccountMove, self).post()
        send_dian = self._context.get('send_dian', False)
        if send_dian == True:
            if res == True:
                if self._context.get('active_model') == 'account.move':
                    domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'posted')]

                moves = self.env['account.move'].search(domain).filtered('line_ids')
                for move in moves:
                    if move.state == 'posted':
                        move.action_post1()
        return res

    def get_pdf_fact(self):
        for move in self:
            numfact = move.name
            nit = move.GetNitCompany(move.company_id.vat)
            # numfact ='SW12761'
            # nit = '891412809'
            headers = {'content-type': 'text/xml;charset=utf-8'}
            responsews = requests.post(
                "http://facturaagil.com.co/WS_Facturacion_Electronica//api"
                "/ConsultaPDF?Numerofact=" + numfact +
                "&Nit=" + nit, data={},
                headers=headers)
            if responsews.status_code == 200:
                respuesta = eval(responsews.content.decode('utf-8'))
                if 'Respuesta' in respuesta:
                    resultados = respuesta['Respuesta']
                    str_pdf = move.GetResponseWS(resultados)
                    str_byte64 = base64.b64decode(str_pdf)
                    # probando descarga
                    base_url = self.env['ir.config_parameter'].get_param(
                        'web.base.url')
                    attachment_obj = self.env['ir.attachment']
                    files = self.env['ir.attachment'].search(
                        [('access_token', '=', 'RGFPETI')], limit=1)
                    if files:
                        files.write({'name': numfact + ".pdf",
                                     'datas': base64.b64encode(str_byte64)})
                        file_id = files.id

                    else:
                        attachment_id = attachment_obj.create(
                            {'name': numfact + ".pdf", 'type': 'binary',
                             'datas': base64.b64encode(str_byte64),
                             'mimetype': 'application/pdf',
                             'res_name': numfact + 's.pdf',
                             'access_token': 'RGFPETI'})
                        file_id = attachment_id.id
                    download_url = '/web/content/' + str(
                        file_id) + '?mimetype=application/pdf'
                    # download
                    return {
                        "type": "ir.actions.act_url",
                        "url": str(base_url) + str(download_url),
                        "target": "new",
                    }
            else:
                raise UserError(_("No se encuentra información de la factura "
                                  " consultada"
                                  ))


class Company(models.Model):
    _inherit = 'res.company'

    operation_type_id = fields.Many2one("dian.operationtype", string='Tipo de operación', required=True)
    company_type_id = fields.Many2one("dian.companytype", string='Tipo de empresa', required=True)
    document_type_id = fields.Many2one("dian.documenttype", string='Tipo de documento', required=True)
    regime_type = fields.Char(string='Tipo de regimen', required=True)
    fiscal_responsibility_ids = fields.Many2many("dian.fiscalresponsibility", string='Responsabilidades fiscales')
    commercial_registration = fields.Char(string='Matricula mercantil', required=True)

    software_pin = fields.Char(string='PIN del software')
    test_set = fields.Char(string='Test Set')
    software_id = fields.Char(string='ID del software')
    # city_id = fields.Many2one('res.city', string='Ciudad')
    ip_webservice = fields.Char(string='IP WebService')
    ruta_plantilla = fields.Char(string='Ruta Plantilla')



class ResPartner(models.Model):
    _inherit = 'res.partner'

    # city_id = fields.Many2one('res.city', string='Ciudad')
    document_type_id = fields.Many2one("dian.documenttype", string='Tipo de documento', required=True)
    organization_type_id = fields.Many2one('dian.companytype', string='Tipo de organizacion')
    fiscal_responsibility_partner_ids = fields.Many2many("dian.fiscalresponsibility",
                                                         string='Responsabilidades fiscales')
    commercial_registration_partner = fields.Char(string='Matricula mercantil')
    partner_currency_id = fields.Many2one('res.currency', string="Moneda",
                                          help='Campo usado para generar factura DIAN')
    # representation_type_id = fields.Many2one('dian.fiscalresponsibility', string='Tipo de representación')
    # establishment_type_id = fields.Many2one('dian.fiscalresponsibility', string='Tipo de establecimiento')
    # customs_type_ids = fields.Many2many('dian.fiscalresponsibility', string='Usuario aduanero')
    # large_taxpayer = fields.Boolean(string="Gran contribuyente", default=False)
    # simplified_regimen = fields.Boolean(string="Regimen simplificado", default=False)
    # fiscal_regimen = fields.Many2one('dian.fiscalregimen', string='Regimen fiscal')


class ResCountry(models.Model):
    _inherit = 'res.country'

    code_dian = fields.Char(string='Codigo DIAN', readonly=True)


class FiscalRegimen(models.Model):
    _name = 'dian.fiscalregimen'
    _description = 'Regimen fiscal DIAN'

    name = fields.Char(String='Nombre')
    code = fields.Char(String='Codigo')


class AccountTax(models.Model):
    _inherit = 'account.tax'

    type_tax = fields.Many2one('dian.typetax', string='Tipo de impuesto')


class TypeTax(models.Model):
    _name = 'dian.typetax'
    _description = 'Tipo de impuesto DIAN'

    name = fields.Char(string='Nombre')
    code = fields.Char(string='Codigo')
    description = fields.Char(string='Descripción')
    retention = fields.Boolean(string="Retención", default=False)


class OperationType(models.Model):
    _name = 'dian.operationtype'
    _description = 'tipos de operaciones DIAN'

    code = fields.Char(string='Codido', required=True)
    name = fields.Char(string='Nombre', required=True)


class CompanyType(models.Model):
    _name = 'dian.companytype'
    _description = 'tipo de compañia'

    code = fields.Char(string='Codido', required=True)
    name = fields.Char(string='Nombre', required=True)


class DocumentType(models.Model):
    _name = 'dian.documenttype'
    _description = 'tipo de documento'

    code = fields.Char(string='Codido', required=True)
    name = fields.Char(string='Nombre', required=True)


class FiscalResponsibility(models.Model):
    _name = 'dian.fiscalresponsibility'
    _description = 'responsabilidades fiscales'

    name = fields.Char(string='Codido', required=True)
    description = fields.Char(string='Descripción', required=True)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # resolution_id = fields.Many2one('dian.resolution', string='Resolución')
    debit_note = fields.Boolean(string="Nota de débito", default=False)
    '''resolution = fields.Char(string='Resolución de facturación', required=True)
    start_range = fields.Char(string='Rango Inicial', required=True)
    end_range = fields.Char(string='Rango Final', required=True)
    start_date = fields.Datetime(string='Fecha de resolución', required=True)
    end_date = fields.Datetime(string='Fecha de finalización de resolución', required=True)
    technical_key = fields.Char(string='Clave tecnica', required=True)'''


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    # @api.model
    def _create_invoice(self, order, so_line, amount, send_dian=False):
        res = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        send_dian = self._context.get('send_dian', False)
        if send_dian == True:
            if res.state == 'draft':
                move = res.action_post()
                if res.state == 'posted':
                    res.action_post1()
        return res

    '''def create_invoices(self):
        send_dian  = self._context.get('send_dian', False)
        if send_dian == True:
            return ""'''

    '''def create_invoices(self):
        res = super(SaleAdvancePaymentInv, self).create_invoices()
        return res'''


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # @api.model
    '''def _create_invoices(self, grouped=False, final=False):
        res = super(SaleOrder, self)._create_invoices(grouped, final)
        send_dian = self._context.get('send_dian', False)
        if send_dian == True:
            for move in res:
                if move.state == 'draft':
                    move.action_post()
                    if move.state == 'posted':
                        move.action_post1()
        return res'''

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        tipo = None
        if self.payment_term_id:
            if len(self.payment_term_id.line_ids.ids) == 1:
                line = self.payment_term_id.line_ids[0]
                if line.value_amount == 0 and line.days == 0 and line.value == 'balance':
                    tipo = 1
                elif line.days != 0:
                    tipo = 2
            else:
                for term in self.payment_term_id.line_ids:
                    if term.value != 'balance' or term.days != 0:
                        tipo = 2
        res['payment_mean_id'] = tipo
        return res


'''class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    payment_mean_id = fields.Many2one('dian.paymentmean', string='Tipo de pago')'''
