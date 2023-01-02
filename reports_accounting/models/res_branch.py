# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

# Sucursales
class zue_res_branch(models.Model):
    _name = 'zue.res.branch'
    _description = 'Sucursales'

    code = fields.Char(string='Código', required=True)
    name = fields.Char(string='Descripción', required=True)