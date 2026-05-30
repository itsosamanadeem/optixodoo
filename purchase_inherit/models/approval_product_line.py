from collections import defaultdict

from odoo import models, fields, _, api #type:ignore
from odoo.exceptions import UserError #type:ignore
import json
import logging
_logger = logging.getLogger(__name__)

class ApprovalProductLine(models.Model):
    _name="approval.product.line"
    _inherit = ['approval.product.line', 'analytic.mixin']

    @staticmethod
    def _distribution_key(*analytic_ids):
        valid_ids = [str(analytic_id) for analytic_id in analytic_ids if analytic_id]
        return ",".join(valid_ids) if valid_ids else False

    @api.model
    def _domain_department_id_for_user(self):
        """
        Users in `purchase_inherit.raise_pr_for_all_departments` can pick any department.
        Others can only pick their own employee department.
        """
        domain = []
        if not self.env.user.has_group('purchase_inherit.raise_pr_for_all_departments'):
            dept = self.env.user.employee_id.department_id
            domain.append(('id', '=', dept.id if dept else False))
        return domain

    department_id = fields.Many2one(
        'hr.department',
        string='Departments',
        domain=_domain_department_id_for_user,
    )
    product_gl_description = fields.Text(string="GL", compute="_compute_product_gl", readonly=True, store=True)
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    price_unit = fields.Monetary(
        compute="_compute_price_unit",
        string="Price",
        store=True,
        readonly=True,
        currency_field='currency_id'
    )
    is_service_product = fields.Boolean(
        string="Is Service Product",
        compute="_compute_is_service_product",
    )
    @api.depends('product_id','product_id.standard_price')
    def _compute_price_unit(self):
        for rec in self:
            rec.price_unit = rec.product_id.standard_price

    @api.depends("product_id", "product_id.type")
    def _compute_is_service_product(self):
        for rec in self:
            rec.is_service_product = rec.product_id.type == "service"
            
    @api.depends('product_id', 'product_id.analytic_gl_id')
    def _compute_product_gl(self):
        for rec in self:
            gl = rec.product_id.analytic_gl_id
            if gl:
                rec.product_gl_description = gl.name
            else:
                rec.product_gl_description = ''
            
    department_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Cost Center",
        related="department_id.analytic_account_id",
        store=True,
        readonly=True,
    )
    department_analytic_city_id = fields.Many2one(
        "account.analytic.account",
        string="City",
        related="department_id.analytic_city_id",
        store=True,
        readonly=True,
    )

    # `approval.product.line` is used by `approvals_purchase` to generate purchase orders.
    # Currency must always be set to avoid creating/updating a PO with a missing `currency_id`.
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    
    @api.depends('department_analytic_account_id','department_id','product_id')
    def _compute_analytic_distribution(self):
        # Keep the base analytic behavior, then auto-fill from department cost center.
        super()._compute_analytic_distribution()
        for rec in self:
            aa_id = rec.department_analytic_account_id.id
            ac_id = rec.department_analytic_city_id.id
            gl_id = rec.product_id.analytic_gl_id.id
            key = self._distribution_key(aa_id, ac_id, gl_id)
            if key and not rec.analytic_distribution:
                rec.analytic_distribution = {key: 100}

    @api.onchange('department_id','product_id')
    def _onchange_department_id_set_analytic_distribution(self):
        for rec in self:
            if not rec.department_id:
                continue
            aa = rec.department_id.analytic_account_id
            ac = rec.department_id.analytic_city_id
            gl_id = rec.product_id.analytic_gl_id
            key = self._distribution_key(aa.id, ac.id, gl_id.id)
            if key:
                rec.analytic_distribution = {key: 100}
    
    status = fields.Selection([
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], required=True, copy=False, default='approved', tracking=True)
    
    manager_refused = fields.Boolean(
        string="Refused By Department Manager",
        default=False,
        copy=False,
    )
    manager_refused_by_id = fields.Many2one(
        'res.users',
        string="Refused By",
        copy=False,
        readonly=True,
    )
    manager_refused_date = fields.Datetime(
        string="Refused On",
        copy=False,
        readonly=True,
    )

    def _check_products_vendor(self):
        pass
