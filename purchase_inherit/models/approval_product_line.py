from odoo import models, fields, _
from odoo.exceptions import UserError

class ApprovalProductLine(models.Model):
    _inherit = ['approval.product.line', 'analytic.mixin']

    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        tracking=True
    )

class ApprovalForm(models.Model):
    _inherit = 'approval.request'

    def action_confirm(self):
        for request in self:
            departments = request.product_line_ids.mapped('department_ids')
            for department in departments:
                if not department:
                    continue 
                 
                manager_employee = department.manager_id
                
                if not manager_employee:
                    raise UserError(_("Department '%s' has no manager assigned." % department.name))
                
                manager_user = manager_employee.user_id
                if not manager_user:
                    raise UserError(_("Manager '%s' of department '%s' has no linked user." % (manager_employee.name, department.name)))
                
                if manager_user.id not in request.approver_ids.mapped('user_id').ids:
                    existing_sequences = request.approver_ids.mapped('sequence')
                    next_sequence = max(existing_sequences, default=0) + 1
                    request.sudo().write({'approver_ids': [(0, 0, {'user_id': manager_user.id,'required': True,'sequence': next_sequence,})]})

        return super().action_confirm()
    
    def _create_purchase_orders(self):
        super()._create_purchase_orders()
        
        for line in self.product_line_ids:
            if line.purchase_order_line_id:
                po_line = line.purchase_order_line_id
                po_line.department_ids = [(6, 0, line.department_ids.ids)]
                po_line.analytic_distribution = line.analytic_distribution
