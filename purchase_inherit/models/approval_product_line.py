from odoo import models, fields, _, api #type:ignore
from odoo.exceptions import UserError #type:ignore
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
    product_gl_description = fields.Text(string="GL", readonly=True, store=True)
    
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
                if manager_user.id not in request.approver_ids.mapped('user_id').ids:
                    approvers_to_add.append(manager_user.id)
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
            if not request.approver_ids:
                raise UserError(_("You must have at least one approver before confirming."))
        return super().action_confirm()

    def action_create_purchase_orders(self):
        res = super(ApprovalForm, self.sudo()).action_create_purchase_orders()
        self._create_activity()
        if self.env.user.has_group('purchase_inherit.group_scm_user'):
            for rec in self:
                rec._mark_scm_activities_done()
        return res
    
    def _create_purchase_orders(self):
        res = super(ApprovalForm, self.sudo())._create_purchase_orders()
        for line in self.product_line_ids:
            if line.purchase_order_line_id:
                po_line = line.purchase_order_line_id
                po_line.department_id = line.department_id
                po_line.analytic_distribution = line.analytic_distribution
        return res
    
    def _create_activity(self):        
        scm_group = self.env.ref('purchase_inherit.group_scm_user')
        scm_users = scm_group.user_ids
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        model_id = self.env['ir.model']._get('approval.request').id
        for request in self:
            for user in scm_users:
                # Create Activity
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': 'New Purchase Request',
                    'note': f'PR {request.name} requires SCM review',
                    'user_id': user.id,
                    'res_id': request.id,
                    'res_model_id': model_id,
                })
                # Send Email
                if user.partner_id.email:
                    request.message_post(
                        body=f"New Purchase Request {request.name} requires your review.",
                        partner_ids=[user.partner_id.id],
                        subtype_xmlid="mail.mt_comment",
                    )
    
    def _mark_scm_activities_done(self):
        scm_group = self.env.ref('purchase_inherit.group_scm_user')
        scm_user_ids = scm_group.users.ids

        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'approval.request'),
            ('res_id', '=', self.id),
            ('user_id', 'in', scm_user_ids),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id)
        ])

        activities.action_done()