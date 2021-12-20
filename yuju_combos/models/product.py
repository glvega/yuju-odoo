# -*- coding: utf-8 -*-
# File:           product.py
# Author:         Gerardo Lopez
# Copyright:      (C) 2021 All rights reserved by Yuju
# Created:        2021-12-19

from odoo import models, api, fields
from odoo import exceptions
from collections import defaultdict
from ..log.logger import logger
from ..responses import results
import psycopg2

class ProductProduct(models.Model):
    _inherit = "product.product"

    yuju_kit = fields.Many2one('mrp.bom', 'Lista de Material Yuju')


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    @api.model
    def mdk_create(self, product_data, id_shop=None):

        # config = self.env['madkting.config'].get_config()
        # mapping = self.env['yuju.mapping.product']
        products = self.env['product.product']

        variation_attributes = product_data.pop('variation_attributes', None)
        has_variations = True if variation_attributes else False

        is_combo = False
        if product_data.get('is_combo'):
            product_data.pop('is_combo')
            is_combo = True
            if product_data.get('combo_components', []):
                combo_components = product_data.pop('combo_components')
                kit_components = []
                for el in combo_components:
                    product_kit_id = el.get('id_product')
                    product_kit_qty = el.get('qty')

                    if not product_kit_id:
                        return results.error_result(code='id_component_empty',
                                                description='El id del componente no se ha definido')

                    product_kit = products.search([('id_product_madkting', '=', product_kit_id)], limit=1)
                    if not product_kit.id:
                        return results.error_result(code='component_not_mapped',
                                                description='Alguno de los componentes no se ha mapeado')

                    kit_components.append((0, 0, {
                        'product_id' : product_kit.id,
                        'product_qty' : product_kit_qty
                        }))       

        res = super(ProductTemplate, self).mdk_create(product_data, id_shop)

        if res['success'] and is_combo:
            res_data = res['data']
            res_id = res_data.get('id')

            res_product = products.search([('id', '=', res_id)], limit=1)

            try:

                if has_variations:
                    new_bom = self.env['mrp.bom'].create({
                        'product_tmpl_id' : res_product.product_tmpl_id.id,
                        'product_qty' : 1,
                        'type' : 'phantom',
                        'bom_line_ids' : kit_components
                    })                
                else:
                    new_bom = self.env['mrp.bom'].create({
                        'product_id' : res_id, 
                        'product_tmpl_id' : res_product.product_tmpl_id.id,
                        'product_qty' : 1,
                        'type' : 'phantom',
                        'bom_line_ids' : kit_components
                    })
            except Exception as e:
                logger.error(e)
                return results.error_result(code='bom_create',
                                                description='Ocurrio un error al crear la ldm')
            else:                
                res_product.write({'yuju_kit' : new_bom.id})
            
        return res