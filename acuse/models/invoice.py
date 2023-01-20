from odoo import api, fields, models, _
from lxml import etree
import base64
import zipfile
import os
import requests
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import xml.etree.ElementTree as ET
from datetime import datetime

NSMAP = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ccts": "urn:un:unece:uncefact:documentation:2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "qdt": "urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
    "udt": "urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }


class Invoice(models.Model):
    _inherit = 'account.move'

    state_acuse = fields.Selection(selection=[
        ('030', 'Acuse'),
        ('032', 'Recibido'),
        ('000', 'desición'),
        ('031', 'Reclamo'),
        ('033', 'Aceptación expresa'),
        ('034', 'Aceptación tácita'),
    ], string='Estado de acuse', readonly=True, copy=False, tracking=True, default='030')

    estado_acuse = fields.Selection([('000', 'Sin Acuse'),
                                     ('030', 'Acuse de recibo de Factura Electrónica de Venta'),
                                     ('031', 'Reclamo de la Factura Electrónica de Venta'),
                                     ('032', 'Recibo del bien o prestación del servicio'),
                                     ('033', 'Aceptación expresa'),
                                     ('034', 'Aceptación Tácita'),
                                     ], string='Estado acuse', copy=False, default='000', tracking=True)

    fecha_recibo = fields.Datetime(string='fecha recibo')
    dias_recibo = fields.Integer(string='dias recibo', compute='_get_dias_recibo')



    estado_rechazo = fields.Selection(selection=[('01', 'Documento con inconsistencias'),
                                                 ('02', 'Mercancía no entregada totalmente'),
                                                 ('03', 'Mercancía no entregada parcialmente'),
                                                 ('04', 'Servicio no prestado')])

    cufe_fac_proveedor = fields.Char('CUFE factura proveedor')
    invoice_type_ref_proveedor = fields.Char('InvoiceTypeRef proveedor')
    fecha_fac_dian = fields.Datetime('Fecha factura DIAN')
    description_status_dian_acuse = fields.Char('Descripción de estado en la DIAN acuse')
    acuse_ids = fields.One2many('account.acuse', 'move_id', string='Acuses', copy=False, readonly=True)



    @api.depends('fecha_recibo')
    def _get_dias_recibo(self):
        for move in self:
            if move.fecha_recibo:
                ahora = datetime.now()
                diferencia = ahora - move.fecha_recibo
                move.dias_recibo = diferencia.days
            else:
                move.dias_recibo = 0

    def registrar_eventos(self):
        return {
            'name': _('Registrar Acuse'),
            'res_model': 'acuse.import.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'default_move_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def EnviarAcuse(self):
        file = 'plantillaAcuse.xml'

        if self.env.company.ruta_plantilla_acuse:
            ruta_plantilla = self.env.company.ruta_plantilla_acuse + '/' + file
        else:
            ruta_plantilla = file
        full_file = os.path.abspath(os.path.join('', ruta_plantilla))
        try:
            doc_xml = ET.parse(full_file)
        except:
            raise UserError("No se encontró la plantilla en la ruta " + full_file)

        root = doc_xml.getroot()

        for move in self:
            '''Encabezado del acuse'''
            move.LeerAttachment(move)
            encabezado = move.EncabezadoAcuse(move)
            ramaEncabezado = 'AcsHead'
            move.EditaNodos(ramaEncabezado, encabezado, root)
            '''Datos de la empresa'''
            company = move.DatosCompany(move)
            ramaCompany = 'Company'
            move.EditaNodos(ramaCompany, company, root)
            '''Datos del proveedor'''
            supplier = move.DatosSupplier(move)
            ramaSupplier = 'Supplier'
            move.EditaNodos(ramaSupplier, supplier, root)

            '''Si el acuse es de recibido de bienes y servicios'''
            if encabezado['AcsType'] == '030' or encabezado['AcsType'] == '032':
                person = move.DatosPerson(move)
                ramaPerson = 'Person'
                move.EditaNodos(ramaPerson, person, root)

            url = ''

            directorio = "Facturacion/Acuses/" + move.GetNitCompany(move.company_id.vat) + "/"

            if self.env.company.ruta_plantilla_acuse:
                ruta_xml = self.env.company.ruta_plantilla_acuse + "/Acuses/" + move.GetNitCompany(move.company_id.vat) + "/"
            else:
                ruta_xml = directorio

            try:
                os.stat(ruta_xml)
            except:
                os.makedirs(ruta_xml)

            new_file = ruta_xml + move.ref + '.xml'

            doc_xml.write(new_file)

            ip_ws = str(move.company_id.ip_webservice)

            if move.state_acuse == '030':  # acuse
                url = 'http://' + ip_ws + '/api/EnvioAcuseRecibo'
            elif move.state_acuse == '031':  # reclamo
                url = 'http://' + ip_ws + '/api/EnvioAcuseRechazo'
            elif move.state_acuse == '032':  # recibido
                url = 'http://' + ip_ws + '/api/EnvioAcuseRecepcionBienes'
            elif move.state_acuse == '033':  # Aceptación expresa
                url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionExpresa'
            elif move.state_acuse == '034':  # Aceptación táctica
                url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionTacita'

            headers = {'content-type': 'text/xml;charset=utf-8'}

            body = open(new_file, "r").read()

            responsews = requests.post(url, data=body.encode('utf-8'), headers=headers)

            tipodato = type(responsews)
            acuse_aprobado_anterior = "Acuse con numero {0} ya aprobado con los sgtes datos".format(
                encabezado['AcsNum'])
            regla90 = "Regla: 90, Rechazo: Documento procesado anteriormente."
            respuestaws = ""
            if responsews.status_code == 200:
                respuesta = eval(responsews.content.decode('utf-8'))
                if 'Respuesta' in respuesta:
                    resultados = respuesta['Respuesta']
                    respuestaws = move.GetResponseWS(resultados).split(';')

                if respuestaws[0] == 'PROCESADO_CORRECTAMENTE':
                    move.state_acuse = '032'
                    move.description_status_dian_acuse = respuestaws
                    move.journal_id.acuse_sequence_id._next_do()
                elif respuestaws[0] == acuse_aprobado_anterior:
                    if respuestaws[1] == encabezado["InvoiceRef"]:
                        if respuestaws[2] == '030':
                            move.state_acuse = '032'
                            move.description_status_dian_acuse = respuestaws[0]
                            move.journal_id.acuse_sequence_id._next_do()
                        elif respuestaws[2] == '032':
                            move.state_acuse = '000'
                            move.description_status_dian_acuse = respuestaws[0]
                            move.journal_id.acuse_sequence_id._next_do()
                        else:
                            move.description_status_dian_acuse = respuestaws[0]
                            move.state_acuse = respuestaws[2]
                            move.journal_id.acuse_sequence_id._next_do()
                    else:
                        move.description_status_dian_acuse = respuestaws[0] + ';' + respuestaws[1]
                elif respuestaws[0] == regla90:
                    move.description_status_dian_acuse = respuestaws[0] + ", vuelva a enviar."
                    move.journal_id.acuse_sequence_id._next_do()
                elif respuestaws[0] == "El evento registrado para el acuse ya existe, con los sgtes datos ":
                    if respuestaws[1] == '030':
                        move.state_acuse = '032'
                        move.description_status_dian_acuse = respuestaws[0]
                        move.journal_id.acuse_sequence_id._next_do()
                    elif respuestaws[1] == '032':
                        move.state_acuse = '000'
                        move.description_status_dian_acuse = respuestaws[0]
                        move.journal_id.acuse_sequence_id._next_do()
                    else:
                        move.description_status_dian_acuse = respuestaws[0]
                        move.state_acuse = respuestaws[1]
                        move.journal_id.acuse_sequence_id._next_do()
                else:
                    move.description_status_dian_acuse = respuestaws[0]
            elif responsews.status_code == 500:
                raise UserError("Error en la conexión al Web service")

    def EnviarRecibido(self):
        file = 'plantillaAcuse.xml'

        if self.env.company.ruta_plantilla_acuse:
            ruta_plantilla = self.env.company.ruta_plantilla_acuse + '/' + file
        else:
            ruta_plantilla = file
        full_file = os.path.abspath(os.path.join('', ruta_plantilla))
        try:
            doc_xml = ET.parse(full_file)
        except:
            raise UserError("No se encontró la plantilla en la ruta " + full_file)

        root = doc_xml.getroot()

        for move in self:
            '''Encabezado del acuse'''
            encabezado = move.EncabezadoAcuse(move)
            ramaEncabezado = 'AcsHead'
            move.EditaNodos(ramaEncabezado, encabezado, root)
            '''Datos de la empresa'''
            company = move.DatosCompany(move)
            ramaCompany = 'Company'
            move.EditaNodos(ramaCompany, company, root)
            '''Datos del proveedor'''
            supplier = move.DatosSupplier(move)
            ramaSupplier = 'Supplier'
            move.EditaNodos(ramaSupplier, supplier, root)

            '''Si el acuse es de recibido de bienes y servicios'''
            if encabezado['AcsType'] == '030' or encabezado['AcsType'] == '032':
                person = move.DatosPerson(move)
                ramaPerson = 'Person'
                move.EditaNodos(ramaPerson, person, root)

            url = ''

            directorio = "Facturacion/Acuses/" + move.GetNitCompany(move.company_id.vat) + "/"

            if self.env.company.ruta_plantilla_acuse:
                ruta_xml = self.env.company.ruta_plantilla_acuse + "/Acuses/" + move.GetNitCompany(
                    move.company_id.vat) + "/"
            else:
                ruta_xml = directorio

            try:
                os.stat(ruta_xml)
            except:
                os.makedirs(ruta_xml)

            new_file = ruta_xml + move.ref + '.xml'

            doc_xml.write(new_file)

            ip_ws = str(move.company_id.ip_webservice)

            if move.state_acuse == '030':  # acuse
                url = 'http://' + ip_ws + '/api/EnvioAcuseRecibo'
            elif move.state_acuse == '031':  # reclamo
                url = 'http://' + ip_ws + '/api/EnvioAcuseRechazo'
            elif move.state_acuse == '032':  # recibido
                url = 'http://' + ip_ws + '/api/EnvioAcuseRecepcionBienes'
            elif move.state_acuse == '033':  # Aceptación expresa
                url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionExpresa'
            elif move.state_acuse == '034':  # Aceptación táctica
                url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionTacita'

            headers = {'content-type': 'text/xml;charset=utf-8'}

            body = open(new_file, "r").read()

            responsews = requests.post(url, data=body.encode('utf-8'), headers=headers)

            tipodato = type(responsews)
            acuse_aprobado_anterior = "Acuse con numero {0} ya aprobado con los sgtes datos".format(
                encabezado['AcsNum'])
            regla90 = "Regla: 90, Rechazo: Documento procesado anteriormente."
            respuestaws = ""
            if responsews.status_code == 200:
                respuesta = eval(responsews.content.decode('utf-8'))
                if 'Respuesta' in respuesta:
                    resultados = respuesta['Respuesta']
                    respuestaws = move.GetResponseWS(resultados).split(';')

                if respuestaws[0] == 'PROCESADO_CORRECTAMENTE':
                    move.state_acuse = '000'
                    move.description_status_dian_acuse = respuestaws[0]
                    move.journal_id.acuse_sequence_id._next_do()
                elif respuestaws[0] == acuse_aprobado_anterior:
                    if respuestaws[1] == encabezado["InvoiceRef"]:
                        if respuestaws[2] == '030':
                            move.state_acuse = '032'
                            move.description_status_dian_acuse = respuestaws[0]
                            move.journal_id.acuse_sequence_id._next_do()
                        elif respuestaws[2] == '032':
                            move.state_acuse = '000'
                            move.fecha_recibo = datetime.now()
                            move.description_status_dian_acuse = respuestaws[0]
                            move.journal_id.acuse_sequence_id._next_do()
                        else:
                            move.description_status_dian_acuse = respuestaws
                            move.state_acuse = respuestaws[2]
                            move.journal_id.acuse_sequence_id._next_do()
                    else:
                        move.description_status_dian_acuse = respuestaws[0] + ';' + respuestaws[1]
                elif respuestaws[0] == regla90:
                    move.description_status_dian_acuse = respuestaws[0] + ", vuelva a enviar."
                    move.journal_id.acuse_sequence_id._next_do()
                elif respuestaws[0] == "El evento registrado para el acuse ya existe, con los sgtes datos ":
                    if respuestaws[1] == '030':
                        move.state_acuse = '032'
                        move.description_status_dian_acuse = respuestaws[0]
                        move.journal_id.acuse_sequence_id._next_do()
                    elif respuestaws[1] == '032':
                        move.state_acuse = '000'
                        move.fecha_recibo = datetime.now()
                        move.description_status_dian_acuse = respuestaws[0]
                        move.journal_id.acuse_sequence_id._next_do()
                    else:
                        move.description_status_dian_acuse = respuestaws[0]
                        move.state_acuse = respuestaws[1]
                        move.journal_id.acuse_sequence_id._next_do()
                else:
                    move.description_status_dian_acuse = respuestaws[0]
            elif responsews.status_code == 500:
                raise UserError("Error en la conexión al Web service")

    def EnviarAceptacionExpresa(self):
        file = 'plantillaAcuse.xml'

        if self.env.company.ruta_plantilla_acuse:
            ruta_plantilla = self.env.company.ruta_plantilla_acuse + '/' + file
        else:
            ruta_plantilla = file
        full_file = os.path.abspath(os.path.join('', ruta_plantilla))
        try:
            doc_xml = ET.parse(full_file)
        except:
            raise UserError("No se encontró la plantilla en la ruta " + full_file)

        root = doc_xml.getroot()

        for move in self:
            '''Encabezado del acuse'''
            move.state_acuse = '033'
            encabezado = move.EncabezadoAcuse(move)
            ramaEncabezado = 'AcsHead'
            move.EditaNodos(ramaEncabezado, encabezado, root)
            '''Datos de la empresa'''
            company = move.DatosCompany(move)
            ramaCompany = 'Company'
            move.EditaNodos(ramaCompany, company, root)
            '''Datos del proveedor'''
            supplier = move.DatosSupplier(move)
            ramaSupplier = 'Supplier'
            move.EditaNodos(ramaSupplier, supplier, root)

            url = ''

            directorio = "Facturacion/Acuses/" + move.GetNitCompany(move.company_id.vat) + "/"

            if self.env.company.ruta_plantilla_acuse:
                ruta_xml = self.env.company.ruta_plantilla_acuse + "/Acuses/" + move.GetNitCompany(
                    move.company_id.vat) + "/"
            else:
                ruta_xml = directorio

            try:
                os.stat(ruta_xml)
            except:
                os.makedirs(ruta_xml)

            new_file = ruta_xml + move.ref + '.xml'

            doc_xml.write(new_file)

            ip_ws = str(move.company_id.ip_webservice)

            if move.state_acuse == '030':  # acuse
                url = 'http://' + ip_ws + '/api/EnvioAcuseRecibo'
            elif move.state_acuse == '031':  # reclamo
                url = 'http://' + ip_ws + '/api/EnvioAcuseRechazo'
            elif move.state_acuse == '032':  # recibido
                url = 'http://' + ip_ws + '/api/EnvioAcuseRecepcionBienes'
            elif move.state_acuse == '033':  # Aceptación expresa
                url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionExpresa'
            elif move.state_acuse == '034':  # Aceptación táctica
                url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionTacita'

            headers = {'content-type': 'text/xml;charset=utf-8'}

            body = open(new_file, "r").read()

            responsews = requests.post(url, data=body.encode('utf-8'), headers=headers)

            tipodato = type(responsews)
            acuse_aprobado_anterior = "Acuse con numero {0} ya aprobado con los sgtes datos".format(
                encabezado['AcsNum'])
            regla90 = "Regla: 90, Rechazo: Documento procesado anteriormente."
            respuestaws = ""
            if responsews.status_code == 200:
                respuesta = eval(responsews.content.decode('utf-8'))
                if 'Respuesta' in respuesta:
                    resultados = respuesta['Respuesta']
                    respuestaws = move.GetResponseWS(resultados).split(';')

                if respuestaws[0] == 'PROCESADO_CORRECTAMENTE':
                    move.description_status_dian_acuse = respuestaws
                    move.journal_id.acuse_sequence_id._next_do()
                elif respuestaws[0] == acuse_aprobado_anterior:
                    if respuestaws[1] == encabezado["InvoiceRef"]:
                        if respuestaws[2] == '030':
                            move.description_status_dian_acuse = respuestaws[0]
                            move.state_acuse = '032'
                            move.journal_id.acuse_sequence_id._next_do()
                        elif respuestaws[2] == '032':
                            move.description_status_dian_acuse = respuestaws[0]
                            move.state_acuse = '000'
                            move.journal_id.acuse_sequence_id._next_do()
                        else:
                            move.description_status_dian_acuse = respuestaws[0]
                            move.state_acuse = respuestaws[2]
                            move.journal_id.acuse_sequence_id._next_do()
                    else:
                        move.description_status_dian_acuse = respuestaws[0] + ';' + respuestaws[1]
                        move.state_acuse = '000'
                elif respuestaws[0] == regla90:
                    move.description_status_dian_acuse = respuestaws[0] + ", vuelva a enviar."
                    move.journal_id.acuse_sequence_id._next_do()
                elif respuestaws[0] == "El evento registrado para el acuse ya existe, con los sgtes datos ":
                    if respuestaws[1] == '030':
                        move.state_acuse = '032'
                        move.description_status_dian_acuse = respuestaws[0]
                        move.journal_id.acuse_sequence_id._next_do()
                    elif respuestaws[1] == '032':
                        move.state_acuse = '000'
                        move.description_status_dian_acuse = respuestaws[0]
                        move.journal_id.acuse_sequence_id._next_do()
                    else:
                        move.description_status_dian_acuse = respuestaws[0]
                        move.state_acuse = respuestaws[1]
                        move.journal_id.acuse_sequence_id._next_do()
                else:
                    move.description_status_dian_acuse = respuestaws[0]
                    move.state_acuse = '000'

            elif responsews.status_code == 500:
                raise UserError("Error en la conexión al Web service")

    def EnviarAceptacionTacita(self):
        file = 'plantillaAcuse.xml'

        if self.env.company.ruta_plantilla_acuse:
            ruta_plantilla = self.env.company.ruta_plantilla_acuse + '/' + file
        else:
            ruta_plantilla = file
        full_file = os.path.abspath(os.path.join('', ruta_plantilla))
        try:
            doc_xml = ET.parse(full_file)
        except:
            raise UserError("No se encontró la plantilla en la ruta " + full_file)

        root = doc_xml.getroot()

        for move in self:

            ahora = datetime.now()
            diferencia = ahora - move.fecha_recibo
            if diferencia.days <= 3:
                raise UserError("Para realizar aceptación tacita deben pasar mas de 3 dias de la fecha de recibo  \n Fecha recibo: " + str(move.fecha_recibo) )

            '''Encabezado del acuse'''
            move.state_acuse = '034'
            encabezado = move.EncabezadoAcuse(move)
            ramaEncabezado = 'AcsHead'
            move.EditaNodos(ramaEncabezado, encabezado, root)
            '''Datos de la empresa'''
            company = move.DatosCompany(move)
            ramaCompany = 'Company'
            move.EditaNodos(ramaCompany, company, root)
            '''Datos del proveedor'''
            supplier = move.DatosSupplier(move)
            ramaSupplier = 'Supplier'
            move.EditaNodos(ramaSupplier, supplier, root)

            url = ''

            directorio = "Facturacion/Acuses/" + move.GetNitCompany(move.company_id.vat) + "/"

            if self.env.company.ruta_plantilla_acuse:
                ruta_xml = self.env.company.ruta_plantilla_acuse + "/Acuses/" + move.GetNitCompany(
                    move.company_id.vat) + "/"
            else:
                ruta_xml = directorio

            try:
                os.stat(ruta_xml)
            except:
                os.makedirs(ruta_xml)

            new_file = ruta_xml + move.name + '.xml'

            doc_xml.write(new_file)

            ip_ws = str(move.company_id.ip_webservice)
            url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionTacita'

            headers = {'content-type': 'text/xml;charset=utf-8'}

            body = open(new_file, "r").read()

            responsews = requests.post(url, data=body.encode('utf-8'), headers=headers)

            tipodato = type(responsews)
            resultados = ""
            respuestaws = ""
            if responsews.status_code == 200:
                respuesta = eval(responsews.content.decode('utf-8'))
                if 'Respuesta' in respuesta:
                    resultados = respuesta['Respuesta']
                    respuestaws = move.GetResponseWS(resultados)

                if respuestaws == 'PROCESADO_CORRECTAMENTE':
                    move.estado_acuse = '034'
                    move.description_status_dian_acuse = respuestaws
                    move.journal_id.acuse_sequence_id._next_do()
                """else:
                    move.description_status_dian_acuse = respuestaws
                    move.state_acuse = '000'"""
            elif responsews.status_code == 500:
                raise UserError("Error en la conexión al Web service")

    def EnviarRechazo(self):
        file = 'plantillaAcuse.xml'

        if self.env.company.ruta_plantilla_acuse:
            ruta_plantilla = self.env.company.ruta_plantilla_acuse + '/' + file
        else:
            ruta_plantilla = file
        full_file = os.path.abspath(os.path.join('', ruta_plantilla))
        try:
            doc_xml = ET.parse(full_file)
        except:
            raise UserError("No se encontró la plantilla en la ruta " + full_file)

        root = doc_xml.getroot()

        for move in self:
            '''Encabezado del acuse'''
            move.state_acuse = '031'
            encabezado = move.EncabezadoAcuse(move)
            ramaEncabezado = 'AcsHead'
            move.EditaNodos(ramaEncabezado, encabezado, root)
            '''Datos de la empresa'''
            company = move.DatosCompany(move)
            ramaCompany = 'Company'
            move.EditaNodos(ramaCompany, company, root)
            '''Datos del proveedor'''
            supplier = move.DatosSupplier(move)
            ramaSupplier = 'Supplier'
            move.EditaNodos(ramaSupplier, supplier, root)

            url = ''

            directorio = "Facturacion/Acuses/" + move.GetNitCompany(move.company_id.vat) + "/"

            if self.env.company.ruta_plantilla_acuse:
                ruta_xml = self.env.company.ruta_plantilla_acuse + "/Acuses/" + move.GetNitCompany(
                    move.company_id.vat) + "/"
            else:
                ruta_xml = directorio

            try:
                os.stat(ruta_xml)
            except:
                os.makedirs(ruta_xml)

            new_file = ruta_xml + move.ref + '.xml'

            doc_xml.write(new_file)

            ip_ws = str(move.company_id.ip_webservice)

            if move.state_acuse == '030':  # acuse
                url = 'http://' + ip_ws + '/api/EnvioAcuseRecibo'
            elif move.state_acuse == '031':  # reclamo
                url = 'http://' + ip_ws + '/api/EnvioAcuseRechazo'
            elif move.state_acuse == '032':  # recibido
                url = 'http://' + ip_ws + '/api/EnvioAcuseRecepcionBienes'
            elif move.state_acuse == '033':  # Aceptación expresa
                url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionExpresa'
            elif move.state_acuse == '034':  # Aceptación táctica
                url = 'http://' + ip_ws + '/api/EnvioAcuseAceptacionTacita'

            headers = {'content-type': 'text/xml;charset=utf-8'}

            body = open(new_file, "r").read()

            responsews = requests.post(url, data=body.encode('utf-8'), headers=headers)

            tipodato = type(responsews)
            acuse_aprobado_anterior = "Acuse con numero {0} ya aprobado con los sgtes datos".format(
                encabezado['AcsNum'])
            regla90 = "Regla: 90, Rechazo: Documento procesado anteriormente."
            respuestaws = ""
            if responsews.status_code == 200:
                respuesta = eval(responsews.content.decode('utf-8'))
                if 'Respuesta' in respuesta:
                    resultados = respuesta['Respuesta']
                    respuestaws = move.GetResponseWS(resultados).split(';')

                if respuestaws[0] == 'PROCESADO_CORRECTAMENTE':
                    move.description_status_dian_acuse = respuestaws
                    move.journal_id.acuse_sequence_id._next_do()
                elif respuestaws[0] == acuse_aprobado_anterior:
                    if respuestaws[1] == encabezado["InvoiceRef"]:
                        if respuestaws[2] == '030':
                            move.description_status_dian_acuse = respuestaws[0]
                            move.state_acuse = '032'
                            move.journal_id.acuse_sequence_id._next_do()
                        elif respuestaws[2] == '032':
                            move.description_status_dian_acuse = respuestaws[0]
                            move.state_acuse = '000'
                            move.journal_id.acuse_sequence_id._next_do()
                        else:
                            move.description_status_dian_acuse = respuestaws[0]
                            move.state_acuse = respuestaws[2]
                            move.journal_id.acuse_sequence_id._next_do()
                    else:
                        move.description_status_dian_acuse = respuestaws[0] + ';' + respuestaws[1]
                        move.state_acuse = '000'
                elif respuestaws[0] == regla90:
                    move.description_status_dian_acuse = respuestaws[0] + ", vuelva a enviar."
                    move.journal_id.acuse_sequence_id._next_do()
                elif respuestaws[0] == "El evento registrado para el acuse ya existe, con los sgtes datos ":
                    if respuestaws[1] == '030':
                        move.state_acuse = '032'
                        move.description_status_dian_acuse = respuestaws[0]
                        move.journal_id.acuse_sequence_id._next_do()
                    elif respuestaws[1] == '032':
                        move.state_acuse = '000'
                        move.description_status_dian_acuse = respuestaws[0]
                        move.journal_id.acuse_sequence_id._next_do()
                    else:
                        move.description_status_dian_acuse = respuestaws[0]
                        move.state_acuse = respuestaws[1]
                        move.journal_id.acuse_sequence_id._next_do()
                else:
                    move.description_status_dian_acuse = respuestaws[0]
                    move.state_acuse = '000'

            elif responsews.status_code == 500:
                raise UserError("Error en la conexión al Web service")

    # def LeerAttachment(self, move):
    #     attachments = move.env['ir.attachment'].search([('res_model', '=', 'account.move'), ('res_id', '=', move.id)])
    #     if len(attachments) > 0:
    #         for attach in attachments:
    #             archivo = open(attach._full_path(attach.store_fname), 'rb').read()
    #             if move.env.company.ruta_plantilla_acuse:
    #                 ruta = move.env.company.ruta_plantilla_acuse + '/'
    #             else:
    #                 ruta = 'temporal/'
    #             name = attach.name
    #             if name.find(".zip") != -1:
    #                 full_ruta = os.path.abspath(os.path.join('', ruta))
    #                 if not os.path.exists(full_ruta):
    #                     os.makedirs(full_ruta)
    #
    #                 with open(full_ruta + "/temp.zip", "wb") as tmp:
    #                     tmp.write(archivo)
    #                     name_zip = full_ruta + "/temp.zip"
    #
    #                 if zipfile.is_zipfile(name_zip):
    #                     with zipfile.ZipFile(name_zip, 'r') as obj_zip:
    #                         FileNames = obj_zip.namelist()
    #                         for fileName in FileNames:
    #                             if fileName.endswith('.xml'):
    #                                 attach = ET.parse(name_zip)
    #                                 nit_proveedor = attach.find('.//cac:SenderParty/cac:PartyTaxScheme/cbc:CompanyID',
    #                                                         namespaces=NSMAP).text
    #                                 if nit_proveedor != move.GetNitCompany(move.partner_id.vat):
    #                                     raise ValidationError('El NIT del xml no corresponde al NIT del proveedor de esta factura')
    #                                 firmadaText = attach.find('.//cac:Attachment/cac:ExternalReference/cbc:Description',
    #                                                           namespaces=NSMAP)
    #                                 firmada = ET.fromstring(firmadaText.text)
    #                                 InvoiceTypeRef = firmada.find('.//cbc:InvoiceTypeCode', namespaces=NSMAP).text
    #                                 CUFE = attach.find('.//cbc:UUID', namespaces=NSMAP).text
    #                                 fecha_factura = attach.find('.//cbc:IssueDate', namespaces=NSMAP).text.replace('-',
    #                                                                                                                '/')
    #                                 hora_factura = attach.find('.//cbc:IssueTime', namespaces=NSMAP).text.split('-')[0]
    #                                 fecha_completa = fecha_factura + ' ' + hora_factura
    #                                 numero_factura = attach.find('.//cbc:ParentDocumentID', namespaces=NSMAP).text
    #     elif move.attachment_ids:
    #         for attach in move.attachment_ids:
    #             archivo = open(attach._full_path(attach.store_fname), 'rb').read()
    #             if move.env.company.ruta_plantilla_acuse:
    #                 ruta = move.env.company.ruta_plantilla_acuse + '/'
    #             else:
    #                 ruta = 'temporal/'
    #             name = attach.name
    #             if name.endswith('.zip'):
    #                 full_ruta = os.path.abspath(os.path.join('', ruta))
    #                 if not os.path.exists(full_ruta):
    #                     os.makedirs(full_ruta)
    #
    #                 with open(full_ruta + "/temp.zip", "wb") as tmp:
    #                     tmp.write(archivo)
    #                     name_zip = full_ruta + "/temp.zip"
    #
    #                 if zipfile.is_zipfile(name_zip):
    #                     with zipfile.ZipFile(name_zip, 'r') as obj_zip:
    #                         FileNames = obj_zip.namelist()
    #                         for fileName in FileNames:
    #                             if fileName.endswith('.xml'):
    #                                 attach = ET.parse(name_zip)
    #                                 nit_proveedor = attach.find('.//cac:SenderParty/cac:PartyTaxScheme/cbc:CompanyID',
    #                                                             namespaces=NSMAP).text
    #                                 if nit_proveedor != move.GetNitCompany(move.partner_id.vat):
    #                                     raise ValidationError(
    #                                         'El NIT del xml no corresponde al NIT del proveedor de esta factura')
    #                                 firmadaText = attach.find('.//cac:Attachment/cac:ExternalReference/cbc:Description',
    #                                                           namespaces=NSMAP)
    #                                 firmada = ET.fromstring(firmadaText.text)
    #                                 InvoiceTypeRef = firmada.find('.//cbc:InvoiceTypeCode', namespaces=NSMAP).text
    #                                 CUFE = attach.find('.//cbc:UUID', namespaces=NSMAP).text
    #                                 fecha_factura = attach.find('.//cbc:IssueDate', namespaces=NSMAP).text.replace('-',
    #                                                                                                                '/')
    #                                 hora_factura = attach.find('.//cbc:IssueTime', namespaces=NSMAP).text.split('-')[0]
    #                                 fecha_completa = fecha_factura + ' ' + hora_factura
    #                                 numero_factura = attach.find('.//cbc:ParentDocumentID', namespaces=NSMAP).text
    #             else:
    #                 if name.endswith('.xml'):
    #                     full_ruta = os.path.abspath(os.path.join('', ruta))
    #                     if not os.path.exists(full_ruta):
    #                         os.makedirs(full_ruta)
    #
    #                     archivo = open(attach._full_path(attach.store_fname), 'rb').read()
    #
    #                     with open(full_ruta + "/temp.xml", "wb") as tmp:
    #                         tmp.write(archivo)
    #                         name_zip = full_ruta + "/temp.xml"
    #
    #                     attach = ET.parse(name_zip)
    #                     nit_proveedor = attach.find('.//cac:SenderParty/cac:PartyTaxScheme/cbc:CompanyID',
    #                                                 namespaces=NSMAP).text
    #                     if nit_proveedor != move.GetNitCompany(move.partner_id.vat):
    #                         raise ValidationError('El NIT del xml no corresponde al NIT del proveedor de esta factura')
    #                     firmadaText = attach.find('.//cac:Attachment/cac:ExternalReference/cbc:Description',
    #                                               namespaces=NSMAP)
    #                     firmada = ET.fromstring(firmadaText.text)
    #                     InvoiceTypeRef = firmada.find('.//cbc:InvoiceTypeCode', namespaces=NSMAP).text
    #                     CUFE = attach.find('.//cbc:UUID', namespaces=NSMAP).text
    #                     fecha_factura = attach.find('.//cbc:IssueDate', namespaces=NSMAP).text.replace('-',
    #                                                                                                    '/')
    #                     hora_factura = attach.find('.//cbc:IssueTime', namespaces=NSMAP).text.split('-')[0]
    #                     fecha_completa = fecha_factura + ' ' + hora_factura
    #                     numero_factura = attach.find('.//cbc:ParentDocumentID', namespaces=NSMAP).text
    #
    #     move.write({'ref': numero_factura, 'fecha_fac_dian': fecha_completa.replace('/', '-'),
    #                 'cufe_fac_proveedor': CUFE, 'invoice_type_ref_proveedor': InvoiceTypeRef})

    def LeerAttachment(self, move):
        if move.attachment_ids:
            for attach in move.attachment_ids:
                name = attach.name
                if name.endswith('.xml') or attach.name.endswith('.XML') or attach.name.endswith('.Xml'):
                    archivo = base64.b64decode(attach.datas).decode("utf-8")

                    try:
                        attach = ET.fromstring(archivo)
                    except:
                        raise ValidationError('Error al leer el xml')

                    firmadaText = attach.find('.//cac:Attachment/cac:ExternalReference/cbc:Description',
                                              namespaces=NSMAP)
                    try:
                        firmada = ET.fromstring(firmadaText.text)
                    except:
                        raise ValidationError('No obtuvo la firmada')

                    nit_proveedor = firmada.find(
                        './/cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID',
                        namespaces=NSMAP).text
                    print(nit_proveedor)
                    nit_partner = move.GetNitCompany(move.partner_id.vat)
                    if nit_proveedor != nit_partner:
                        raise ValidationError('El NIT {0} del xml no corresponde al NIT {1} del proveedor de esta factura'.format(
                                nit_proveedor, nit_partner))

                    InvoiceTypeRef = firmada.find('./cbc:InvoiceTypeCode', namespaces=NSMAP).text
                    CUFE = firmada.find('./cbc:UUID', namespaces=NSMAP).text
                    fecha_factura = firmada.find('./cbc:IssueDate', namespaces=NSMAP).text.replace('-', '/')
                    fecha_completa = fecha_factura
                    numero_factura = firmada.find('./cbc:ID', namespaces=NSMAP).text
                    organization_type_id = firmada.find(
                        './/cac:AccountingSupplierParty/cbc:AdditionalAccountID',
                        namespaces=NSMAP)
                    if organization_type_id.text:
                        move.partner_id.organization_type_id = int(organization_type_id.text)
                    print(InvoiceTypeRef, CUFE)
                else:
                    raise ValidationError('No hay attachments')
        else:
            raise ValidationError('Debe adjuntar un xml')

        move.write({'ref': numero_factura if numero_factura else 'No cargo numero de factura',
                    'fecha_fac_dian': fecha_completa.replace('/', '-') if fecha_completa else False,
                    'cufe_fac_proveedor': CUFE if CUFE else 'No hay CUFE',
                    'invoice_type_ref_proveedor': InvoiceTypeRef if InvoiceTypeRef else 'No hay InvoiceTypeRef'})

    def EncabezadoAcuse(self, move):
        # AcsHead
        AcsHead_Company = ''
        AcsType = ''
        AcsNum = ''
        InvoiceRef = ''
        RejectType = ''
        RejectName = ''
        InvoiceTypeRef = ''
        InvoiceDateRef = ''
        InvoiceCufeRef = ''
        TecnicalKey = ''
        IdSoftware = ''
        TestSet = ''
        PinSoftware = ''
        Note = ''
        if move.state_acuse == '030':  # acuse
            AcsType = '030'
        elif move.state_acuse == '031':  # reclamo
            AcsType = '031'
        elif move.state_acuse == '032':  # recibido
            AcsType = '032'
        elif move.state_acuse == '033':  # Aceptación expresa
            AcsType = '033'
        elif move.state_acuse == '034':  # Aceptación táctica
            AcsType = '034'
            acuse_bienes = move.acuse_ids.filtered(lambda l: l.codigo == '032')
            Note = "Manifiesto bajo la gravedad de juramento que transcurridos 3 días hábiles contados desde " \
                   "la creación del Recibo de bienes y servicios {0} con CUDE {1}, el " \
                   "adquirente {2} identificado con NIT {3} no manifestó expresamente " \
                   "la aceptación o rechazo de la referida factura, ni reclamó en contra de su contenido".format(acuse_bienes.name, acuse_bienes.cude, move.partner_id.name, move.partner_id.vat )

        num_sig = move.journal_id.acuse_sequence_id.number_next_actual
        AcsNum = move.journal_id.acuse_sequence_id.prefix + str(num_sig)

        if move.state_acuse == '031':
            if move.estado_rechazo:
                if move.estado_rechazo == '01':
                    RejectType = '01'
                elif move.estado_rechazo == '02':
                    RejectType = '02'
                elif move.estado_rechazo == '03':
                    RejectType = '03'
                elif move.estado_rechazo == '04':
                    RejectType = '04'
            else:
                raise ValidationError('Debe elegir un estado de rechazo')

            RejectName = move.estado_rechazo

        TecnicalKey = move.journal_id.sequence_id.resolution_id.resolution_technical_key
        IdSoftware = move.company_id.software_id
        TestSet = move.company_id.test_set
        PinSoftware = move.company_id.software_pin

        datos = dict(Company=move.GetNitCompany(move.company_id.vat),
                     AcsType=AcsType,
                     AcsNum=AcsNum,
                     InvoiceRef=move.ref if move.state_acuse != '034' else move.name,
                     RejectType=RejectType,
                     RejectName=RejectName,
                     InvoiceTypeRef=move.invoice_type_ref_proveedor if move.state_acuse != '034' else "01",
                     InvoiceCufeRef=move.cufe_fac_proveedor if move.state_acuse != '034' else " ",
                     InvoiceDateRef=move.fecha_fac_dian.strftime('%Y-%m-%d') if move.state_acuse != '034' else " ",
                     TecnicalKey=TecnicalKey,
                     IdSoftware=IdSoftware,
                     TestSet=TestSet,
                     PinSoftware=PinSoftware,
                     Note=Note)

        return datos

    def DatosCompany(self, move):
        # company
        company_company = ''
        IdentificationType = ''
        Name = ''
        CompanyType_c = ''

        datoscompany = dict(company=move.GetNitCompany(move.company_id.vat),
                            IdentificationType=move.company_id.document_type_id.code, Name=move.company_id.name,
                            CompanyType_c=move.company_id.company_type_id.code, )

        return datoscompany

    def DatosSupplier(self, move):
        # Supplier
        Company = move.GetNitCompany(move.company_id.vat)
        CustID = move.TypeDocumentCust(move.partner_id.l10n_latam_identification_type_id.l10n_co_document_code)
        CustNum = move.GetNitCompany(move.partner_id.vat)
        supplier_name = move.partner_id.name
        supplier_companyType_c = move.partner_id.organization_type_id.code
        EMailAddress = move.partner_id.email

        datossupplier = dict(Company=Company, CustID=CustID, CustNum=CustNum, Name=supplier_name,
                             CompanyType_c=supplier_companyType_c, EMailAddress=EMailAddress)
        return datossupplier

    def DatosPerson(self, move):
        # Person
        person_identificationType = move.company_id.document_type_id.code
        PersonNum = move.GetNitCompany(move.company_id.vat)
        Names = move.company_id.name
        SurNames = move.company_id.name
        JobTitle = 'N/A'
        Department = 'N/A'

        datosperson = dict(IdentificationType=person_identificationType, PersonNum=PersonNum, Names=Names,
                           SurNames=SurNames, JobTitle=JobTitle, Department=Department)
        return datosperson
