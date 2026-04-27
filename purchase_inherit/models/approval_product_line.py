from odoo import models, fields, _, api
from odoo.exceptions import UserError
import json
import logging
_logger = logging.getLogger(__name__)

class ApprovalProductLine(models.Model):
    _name="approval.product.line"
    _inherit = ['approval.product.line', 'analytic.mixin']

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
    product_gl_description = fields.Text(string="Product Description", readonly=True)
    
    @api.onchange('product_id')
    def product_gl_onchange(self):
        for rec in self:
            rec.product_gl_description = rec.product_id.property_account_expense_id.code + ' ' + rec.product_id.property_account_expense_id.name if rec.product_id and rec.product_id.property_account_expense_id else ''
            
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
            if (rec.department_analytic_account_id or rec.department_analytic_city_id) and not rec.analytic_distribution and rec.product_id.analytic_gl_id:
                rec.analytic_distribution = {f"{rec.department_analytic_account_id.id},{rec.department_analytic_city_id.id},{rec.product_id.analytic_gl_id.id}": 100}

    @api.onchange('department_id','product_id')
    def _onchange_department_id_set_analytic_distribution(self):
        for rec in self:
            if not rec.department_id:
                continue
            aa = rec.department_id.analytic_account_id
            ac = rec.department_id.analytic_city_id
            gl_id = rec.product_id.analytic_gl_id
            if aa or ac:
                rec.analytic_distribution = {f"{aa.id},{ac.id},{gl_id.id}": 100}

    def _check_products_vendor(self):
        pass

class ApprovalForm(models.Model):
    _inherit = 'approval.request'

    def action_confirm(self):
        skip_city_check = self.env.context.get('skip_city_check')

        for request in self:

            departments = request.product_line_ids.mapped('department_id')
            approvers_to_add = []

            for department in departments:
                if not department:
                    continue

                manager_employee = department.manager_id
                if not manager_employee:
                    raise UserError(_("Department '%s' has no manager assigned.") % department.name)

                manager_user = manager_employee.user_id
                if not manager_user:
                    raise UserError(
                        _("Manager '%s' of department '%s' has no linked user.")
                        % (manager_employee.name, department.name)
                    )

                # ✅ City validation (skip only when coming from wizard)
                if not skip_city_check and department.analytic_city_id.name == '000':
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'City Warning',
                        'res_model': 'city.warning.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_request_id': request.id,
                            'default_message': _(
                                "City for department '%s'.\n\n"
                                "is: %s\n"
                                "Do you want to proceed?"
                            ) % (
                                department.name,
                                department.analytic_city_id.name,
                            )
                        }
                    }

                # ✅ Collect approvers (avoid duplicates)
                if manager_user.id not in request.approver_ids.mapped('user_id').ids:
                    approvers_to_add.append(manager_user.id)

            # ✅ Add approvers AFTER loop (safe & deterministic)
            if approvers_to_add:
                existing_sequences = request.approver_ids.mapped('sequence')
                next_sequence = max(existing_sequences, default=0) + 1

                request.sudo().write({
                    'approver_ids': [
                        (0, 0, {
                            'user_id': uid,
                            'required': True,
                            'sequence': next_sequence + i,
                        }) for i, uid in enumerate(approvers_to_add)
                    ]
                })

            # ✅ Final safety check (critical)
            if not request.approver_ids:
                raise UserError(_("You must have at least one approver before confirming."))

        return super().action_confirm()

    def _create_purchase_orders(self):
        res = super()._create_purchase_orders()

        for line in self.product_line_ids:
            if line.purchase_order_line_id:
                po_line = line.purchase_order_line_id
                po_line.department_id = line.department_id
                po_line.analytic_distribution = line.analytic_distribution

        return res