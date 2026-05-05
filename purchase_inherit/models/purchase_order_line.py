from odoo import models, fields, api, _ #type:ignore
from odoo.exceptions import UserError, ValidationError #type:ignore
from odoo.tools.float_utils import float_compare #type:ignore

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @staticmethod
    def _distribution_key(*analytic_ids):
        valid_ids = [str(analytic_id) for analytic_id in analytic_ids if analytic_id]
        return ",".join(valid_ids) if valid_ids else False
    
    department_id = fields.Many2one(
        'hr.department',
        string="Departments",
        required=False,
    )
    is_service_product = fields.Boolean(
        string="Is Service Product",
        compute="_compute_is_service_product",
    )
    
    # def write(self, vals):
    #     if not self.order_id.is_sent_back:
    #         raise UserError("Cannot modify sent-back orders.")
    #     return super().write(vals)

    @api.depends('department_id')
    def _compute_analytic_distribution(self):
        # Keep the base analytic behavior, then auto-fill from department cost center.
        super()._compute_analytic_distribution()
        for rec in self:
            aa_id = rec.department_id.analytic_account_id.id
            ac_id = rec.department_id.analytic_city_id.id
            gl_id = rec.product_id.analytic_gl_id.id
            key = self._distribution_key(aa_id, ac_id, gl_id)
            if key and not rec.analytic_distribution:
                rec.analytic_distribution = {key: 100}

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
            key = self._distribution_key(aa.id, ac.id, gl_id.id)
            if key:
                rec.analytic_distribution = {key: 100}

    amount_to_change = fields.Float(string="Amount to Change", store=True)

    @api.depends("product_id", "product_id.type")
    def _compute_is_service_product(self):
        for rec in self:
            rec.is_service_product = rec.product_id.type == "service"
        
    @api.onchange('product_id', 'product_qty', 'amount_to_change')
    def _change_price_unit(self):
        for rec in self:
            if not rec.product_qty:
                continue
            if rec.product_id.type == "service":
                # Service lines stay manually editable.
                continue

            base_price = rec.product_id.standard_price or 0
            rec.price_unit = base_price + rec.amount_to_change
