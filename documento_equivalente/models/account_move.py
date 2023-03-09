from odoo import models, fields, api
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime
import pytz

class AccountMove(models.Model):
    _inherit = 'account.move'

    doc_period = fields.Many2one('dian.formgentrans', string='Forma de generación y transmisión')
    documento_equivalente = fields.Boolean(string='Documento equivalente', related='journal_id.documento_equivalente')
    note_document_equivalent_concept = fields.Many2one("dian.note.document.equivalent.concept", string='Concepto Nota de ajuste')

    def get_nombreplantilla(self, move):
        tipo = move.GetInvoiceType(move)
        if tipo in ['05', '95']:
            return 'plantillaDS.xml'
        else:
            return super(AccountMove, self).get_nombreplantilla(move)


    def GetInvoiceType(self, datos):
        res = super(AccountMove, self).GetInvoiceType(datos)
        for dato in datos:
            if res == '':
                if dato.move_type == 'in_invoice' and dato.documento_equivalente:
                    return '05'
                elif dato.move_type == 'in_refund' and dato.documento_equivalente:
                    return '95'
            return res

    def get_url_ws(self, invoicetype, move):
        ip_ws = str(move.company_id.ip_webservice)
        url = ''
        if invoicetype == '05':
            return 'http://' + ip_ws + '/api/EnvioDocumentoEquivalente'
        elif invoicetype == '95':
            return 'http://' + ip_ws + '/api/EnvioNotaDocumentoEquivalente'
        else:
            return super(AccountMove, self).get_url_ws(invoicetype, move)

    def create_dict_invoicehead_dian(self, move):
        invoicetype = move.GetInvoiceType(move)
        datos = super(AccountMove, self).create_dict_invoicehead_dian(move)
        resolucion = self.obtener_resolucion_encabezado(move, invoicetype)
        if invoicetype == "05":
            datos['InvoiceComment1'] = ''

            datos.pop('InvoiceTypeRef')
            datos.pop('InvoiceDateRef')
            datos.pop('DueDateRef')
            datos.pop('InvoicePeriod')
            datos.pop('NetWeight')
            datos.pop('PorcAdministracion')
            datos.pop('PorcImprevistos')
            datos.pop('PorcUtilidad')
            datos.pop('GrossWeight')
        elif invoicetype == '95':
            datos['DiscrepansyDescription'] = resolucion['DiscrepansyDescription']
            datos['DiscrepansyCode'] = resolucion['DiscrepansyCode']
        return datos

    def obtener_resolucion_encabezado(self, move, invoice_type):
        if invoice_type == '95':
            return {'InvoiceRef': move.reversed_entry_id.name,
                    'InvoiceTypeRef': move.GetInvoiceType(move.reversed_entry_id),
                    'InvoiceDateRef': move.reversed_entry_id.invoice_date.strftime('%d/%m/%Y %H:%M:%S'),
                    'DueDateRef': move.reversed_entry_id.invoice_date_due.strftime('%d/%m/%Y %H:%M:%S'),
                    'DiscrepansyDescription': move.note_document_equivalent_concept.code,
                    'DiscrepansyCode': move.note_document_equivalent_concept.name,
                    'CMReasonCode_c': '0',
                    'CMReasonDesc_c': '0',
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
                    'TecnicalKey': ' '}
        else:
            return super(AccountMove, self).obtener_resolucion_encabezado(move, invoice_type)


    def get_dict_lineas_fact(self, move):
        invoicetype = move.GetInvoiceType(move)
        datos = super(AccountMove, self).get_dict_lineas_fact(move)
        if invoicetype in ['05', '95']:
            tz = self.env.user.tz
            if tz:
                local_tz = pytz.timezone(tz)
            else:
                local_tz = pytz.utc
            # Get current time
            now = datetime.now(local_tz)
            order_num = " "
            date_order = now.strftime('%d/%m/%Y %H:%M:%S')
            if move.invoice_origin:
                invoice_origin = self.env['purchase.order'].search([('name', '=', move.invoice_origin)])
                if invoice_origin:
                    order_num = invoice_origin.name
                    date_order = invoice_origin.date_approve.strftime('%d/%m/%Y %H:%M:%S')
                else:
                    order_num = move.invoice_origin
                    date_order = invoice_origin.date_approve.strftime('%d/%m/%Y %H:%M:%S')
            datos['datos'][0]['DocPeriod'] = move.doc_period.code if move.doc_period.code else ' '
            datos['datos'][0]['PurchaseDate'] = date_order
        return datos

    def create_dict_customer(self, move):
        invoicetype = move.GetInvoiceType(move)
        if invoicetype in ['05', '95']:
            nit_company = move.GetNitCompany(move.company_id.vat)
            FiscalResposability_c = move.GetResponsibilities(move.company_id.fiscal_responsibility_ids)
            return {'Company': nit_company,
                     'CustID': move.company_id.document_type_id.code,
                     'CustNum': nit_company,
                     'ResaleID': nit_company,
                     'Name': move.company_id.name,
                     'Address1': move.company_id.street,
                     'EMailAddress': move.company_id.email,
                     'PhoneNum': move.company_id.phone,
                     'CurrencyCode': move.currency_id.name,
                     'Country': move.company_id.country_id.name,
                     'CountryCode': move.company_id.country_id.code,
                     'PostalZone': move.company_id.zip,
                     'RegimeType_c': move.company_id.company_type_id.code,
                     'FiscalResposability_c': FiscalResposability_c,
                     'State': move.company_id.state_id.name,
                     'StateNum': move.company_id.state_id.dian_state_code,
                     'City': move.company_id.city_id.name,
                     'CityNum': move.company_id.city_id.code,
                     'CorporateRegistration': move.company_id.commercial_registration}
        else:
            return super(AccountMove, self).create_dict_customer(move)

    def create_dict_company_dian(self, move):
        invoicetype = move.GetInvoiceType(move)
        if invoicetype in ['05', '95']:
            nit_company = move.GetNitCompany(move.company_id.vat)
            CustNum = move.GetNitCompany(move.partner_id.vat)
            CustID = move.TypeDocumentCust(move.partner_id.l10n_latam_identification_type_id.l10n_co_document_code)
            FiscalResposability_partner = self.GetResponsibilities(move.partner_id.fiscal_responsibility_partner_ids)

            tz = self.env.user.tz
            if tz:
                local_tz = pytz.timezone(tz)
            else:
                local_tz = pytz.utc

            # Get current time
            now = datetime.now(local_tz)

            order_num = " "
            date_order = now.strftime('%d/%m/%Y %H:%M:%S')
            if move.invoice_origin:
                invoice_origin = self.env['purchase.order'].search([('name', '=', move.invoice_origin)])
                if invoice_origin:
                    order_num = invoice_origin.name
                    date_order = invoice_origin.date_approve.strftime('%d/%m/%Y %H:%M:%S')
                else:
                    order_num = move.invoice_origin
                    date_order = invoice_origin.date_approve.strftime('%d/%m/%Y %H:%M:%S')
            return {'company': CustNum,
                    'StateTaxID': CustNum,
                    'IdentificationType': CustID,
                    'Name': move.partner_id.name,
                    'RegimeType_c': move.partner_id.organization_type_id.code,
                    'FiscalResposability_c': FiscalResposability_partner,
                    'CompanyType_c': move.partner_id.organization_type_id.code,
                    'State': move.partner_id.state_id.name,
                    'StateNum': move.partner_id.state_id.dian_state_code,
                    'City': move.partner_id.city,
                    'CityNum': move.partner_id.city_id.code,
                    'Address1': move.partner_id.street,
                    'CurrencyCode': move.currency_id.name,
                    'CountryName': move.partner_id.country_id.name,
                    'CountryCode': move.partner_id.country_id.code,
                    'OrderNum': order_num,
                    'DateOrder': date_order,
                    'PostalZone': move.partner_id.zip,
                    'PhoneNum': move.partner_id.phone,
                    'Email': move.partner_id.email,
                    'WebPage': move.partner_id.website,
                    'CorporateRegistration': move.partner_id.commercial_registration_partner,
                    'TypeOfOrigin': move.partner_id.type_of_origin_id.code}
        else:
            return super(AccountMove, self).create_dict_company_dian(move)