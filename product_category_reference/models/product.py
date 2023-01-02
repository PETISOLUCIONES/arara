# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError, Warning
import logging

_logger = logging.getLogger(__name__)

class ProductCategory(models.Model):
    _inherit = 'product.category'

    sequence_id = fields.Many2one('ir.sequence','Category Reference')
    sequence_prefix = fields.Char('Category Prefix', related='sequence_id.prefix')
    account_internal_id = fields.Many2one('account.account')


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    default_code = fields.Char('Internal Reference', index=True, readonly=False)
    default_code_sequence_id = fields.Many2one('ir.sequence','Category Sequence')
    sector = fields.Selection([('s','Servicios'),('i','Impuestos'),('r','Repuestos'),('m','Máquinas')])
    machine_reference = fields.Char(string="Ref. Máquina")
   
    def category_with_sequence(self,categ_id=None):
        if categ_id.sequence_id:
            return categ_id.sequence_id
        category_obj = self.env['product.category'].search([('id','=',categ_id.parent_id.id)])
        if not category_obj.sequence_id and not category_obj.parent_id:
            raise ValidationError(_('Product parent category not have once sequence'))
        if not category_obj.sequence_id and category_obj.parent_id:
            self.category_with_sequence(category_obj.parent_id)
        if category_obj.sequence_id:
            return category_obj.sequence_id
    
    @api.model_create_multi
    def create(self, vals_list):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        templates = super(ProductTemplate, self).create(vals_list)
        if "create_product_product" not in self._context:
            templates._create_variant_ids()

        # This is needed to set given values to first variant after creation
        for template, vals in zip(templates, vals_list):
            category_obj = self.env['product.category'].browse(vals.get('categ_id'))
            related_vals = {}
            if vals.get('barcode'):
                related_vals['barcode'] = vals['barcode']
            if vals.get('default_code'):
                related_vals['default_code'] = vals['default_code']
            if vals.get('standard_price'):
                related_vals['standard_price'] = vals['standard_price']
            if vals.get('volume'):
                related_vals['volume'] = vals['volume']
            if vals.get('weight'):
                related_vals['weight'] = vals['weight']
            # Please do forward port
            if vals.get('packaging_ids'):
                related_vals['packaging_ids'] = vals['packaging_ids']
            if vals.get('default_code'):
                related_vals['default_code'] = vals['default_code']
            else:
                sequence = self.category_with_sequence(category_obj)
                related_vals['default_code'] = sequence.next_by_id() or ''
                related_vals['default_code_sequence_id'] = sequence.id
            if related_vals:
                template.write(related_vals)

        return templates
        
        
    def write(self, vals):
        uom = self.env['uom.uom'].browse(vals.get('uom_id')) or self.uom_id
        uom_po = self.env['uom.uom'].browse(vals.get('uom_po_id')) or self.uom_po_id
        if uom and uom_po and uom.category_id != uom_po.category_id:
            vals['uom_po_id'] = uom.id

        res = super(ProductTemplate, self).write(vals)
        if vals.get('categ_id'):
            category_obj = self.env['product.category'].browse(vals.get('categ_id'))
            sequence = self.category_with_sequence(category_obj)
            if category_obj.id != self.default_code_sequence_id.id:
                if vals.get('default_code'):
                    vals['default_code'] = sequence.next_by_id() or ''
                    vals['default_code_sequence_id'] = sequence.id
        return res
