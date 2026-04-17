# See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'analytic.mixin']

    analytic_distribution_text = fields.Text(company_dependent=True)
    analytic_distribution = fields.Json(inverse="_inverse_analytic_distribution", store=False, precompute=False)
    analytic_account_ids = fields.Many2many('account.analytic.account', compute="_compute_analytic_account_ids", copy=True)

    @api.depends_context('company')
    @api.depends('analytic_distribution_text')
    def _compute_analytic_distribution(self):
        for record in self:
            record.analytic_distribution = json.loads(record.analytic_distribution_text or '{}')

    def _inverse_analytic_distribution(self):
        for record in self:
            record.analytic_distribution_text = json.dumps(record.analytic_distribution)

    @api.depends('analytic_distribution')
    def _compute_analytic_account_ids(self):
        for record in self:
            record.analytic_account_ids = bool(record.analytic_distribution) and self.env['account.analytic.account'].browse(
                list({int(account_id) for ids in record.analytic_distribution for account_id in ids.split(",")})
            ).exists()

    def update_analytic_distribution(self):
        for rec in self:
            for line in rec.order_line:
                line.analytic_distribution = rec.analytic_distribution


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = ['purchase.order.line', 'analytic.mixin']

    @api.onchange('product_id')
    def _onchange_product_analytic(self):
        for line in self:
            if line.order_id.analytic_distribution and not line.analytic_distribution:
                line.analytic_distribution = line.order_id.analytic_distribution    

    @api.model_create_multi
    def create(self, values):
        res = super(PurchaseOrderLine, self).create(values)
        if 'purchase_id' in values and values.get('purchase_id'):
            purchase = self.env['purchase.order'].browse(values['purchase_id'])
            purchase.update_analytic_distribution()
            analytic_distribution = purchase.analytic_distribution or {}
            values['analytic_distribution'] = analytic_distribution
        return res
