from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    department_id = fields.Many2one(
        'hr.department',
        string="Departments",
        required=False,
    )
    @api.depends('department_id')
    def _compute_analytic_distribution(self):
        # Keep the base analytic behavior, then auto-fill from department cost center.
        super()._compute_analytic_distribution()
        for rec in self:
            if (rec.department_id.analytic_account_id or rec.department_id.analytic_city_id) and not rec.analytic_distribution and rec.product_id.analytic_gl_id:
                rec.analytic_distribution = {f"{rec.department_id.analytic_account_id.id},{rec.department_id.analytic_city_id.id},{rec.product_id.analytic_gl_id.id}": 100}

    @api.onchange('department_id')
    def _onchange_department_ids_set_analytic_distribution(self):
        """If exactly one department is selected, auto-fill from its cost center."""
        if 'analytic_distribution' not in self._fields:
            return
        for rec in self:
            if not rec.department_id:
                continue
            aa = rec.department_id.analytic_account_id
            ac = rec.department_id.analytic_city_id
            gl_id = rec.product_id.analytic_gl_id
            if aa or ac:
                rec.analytic_distribution = {f"{aa.id},{ac.id},{gl_id.id}": 100}

    amount_to_change = fields.Float(string="Amount to Change")

    @api.depends('product_qty', 'product_uom_id', 'company_id', 'order_id.partner_id','amount_to_change')
    def _compute_price_unit_and_date_planned_and_name(self):
        super()._compute_price_unit_and_date_planned_and_name()
        for line in self:
            if line.amount_to_change:
                line.price_unit += line.amount_to_change / line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)