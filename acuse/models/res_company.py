from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    ruta_plantilla_acuse = fields.Char('Ruta plantilla recibido',
                                       help='Ruta de la plantilla para enviar el acuse de recibido a la DIAN')