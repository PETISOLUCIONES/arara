from odoo import models, fields, api
import requests
import json
from lxml import html


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def obtener_nit_razon(self):
        ids = self.env.context['active_ids']
        for partner in self.env['res.partner'].search([('id', 'in', ids)]):
            if partner.l10n_latam_identification_type_id.l10n_co_document_code == 'rut':
                if not partner.vat and partner.name:
                    datos = partner.obtener_info_empresa(razon=partner.name)
                    if datos['mensaje_error'] == '':
                        vat = partner.obtener_nit_sindv(
                            datos['rows'][0]['identificacion'].replace(datos['rows'][0]['clase_identificacion'],
                                                                       '').replace(' ', ''))
                        partner.vat_num = vat
                        partner._on_chage_vat()
                        partner._on_chage_vat_dv()
                elif partner.vat:
                    datos = partner.obtener_info_empresa(nit=partner.vat)
                    if datos['mensaje_error'] == '':
                        name = datos['rows'][0]['razon_social']
                        partner.name = name

    def obtener_info_empresa(self, nit=None, razon=None):
        url_rues = 'https://www.rues.org.co/'
        request_rues = requests.Session()
        req = request_rues.get(url_rues)
        t = html.fromstring(req.content)

        if nit:
            auth_nit_string = t.xpath("//form[@id='frmConsultaNIT']/input[@name='__RequestVerificationToken']")[0].value
            data = {
                '__RequestVerificationToken': auth_nit_string,
                'txtNIT': self.obtener_nit_sindv(nit),
                'txtCI': '',
                'txtDV': '',
            }
            url = 'https://www.rues.org.co/RM/ConsultaNIT_json'
        if razon:
            auth_name_string = t.xpath("//form[@id='frmConsultaNombre']/input[@name='__RequestVerificationToken']")[
                0].value
            data = {
                '__RequestVerificationToken': auth_name_string,
                'txtNombre': razon,
            }
            url = 'https://www.rues.org.co/RM/ConsultaNombre_json'

        res = request_rues.post(url, data=data)
        datos = json.loads(res.text)
        return datos

    def obtener_nit_sindv(self, number):
        document = ''
        try:
            if '-' in number:
                document = number[0:number.find('-')]
            else:
                document = number
            return document
        except:
            return document
