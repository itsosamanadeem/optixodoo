from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PurchaseOrder(models.Model):
    _inherit = ["purchase.order",'mail.thread', 'mail.activity.mixin']

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        required=False,
        default=lambda self: self.env.user.employee_id.department_id
    )
    
    def button_confirm(self):
        for order in self:
            if not order.order_line:
                raise UserError(_("Please add at least one line to confirm the purchase order."))

            managers = self.env['res.users']
            for line in order.order_line:
                if line.department_ids:
                    managers |= line.department_ids.mapped('manager_id.user_id').filtered(lambda u:u)
            
            # raise UserError(_("Managers: %s") % managers.mapped('name'))
            for manager in managers:
                if not manager:
                    raise UserError(_("A department manager has no linked user."))
                
                approval_level = self.env['ml.approval.level']

                existing_levels = approval_level.search([
                    ('group_id', '=', order.approval_group_id.id)
                ], order="sequence asc")
                
                # raise UserError(_("Existing Levels: %s") % existing_levels.mapped('name'))
                existing_manager_levels = approval_level.search([
                    ('group_id', '=', order.approval_group_id.id),
                    ('user_ids', 'in', managers.ids)
                ])

                existing_manager_users = existing_manager_levels.mapped('user_ids')
                new_managers = managers - existing_manager_users

                if new_managers:
                    shift_by = len(new_managers)

                    # STEP 1: Temporarily move existing sequences out of range
                    # (avoid unique constraint collision)
                    temp_offset = 1000  # large safe gap
                    for level in existing_levels:
                        level.sudo().write({'sequence': level.sequence + temp_offset})

                    # STEP 2: Assign final shifted sequence
                    for level in existing_levels:
                        level.sudo().write({'sequence': level.sequence - temp_offset + shift_by})

                    # STEP 3: Insert new managers at top
                    for i, manager in enumerate(new_managers, start=1):
                        approval_level.sudo().create({
                            'name': f'Approval for {order.name}',
                            'sequence': i,
                            'group_id': order.approval_group_id.id,
                            'min_amount': 0,
                            'max_amount': 1,
                            'is_recommendation': True,
                            'is_approval': False,
                            'user_ids': [(4, manager.id)],
                        })

                        # Activity
                        self.env['mail.activity'].create({
                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                            'summary': _('Purchase Order Confirmation'),
                            'user_id': manager.id,
                            'res_id': order.id,
                            'res_model_id': self.env['ir.model']._get('purchase.order').id,
                        })
        return super().button_confirm()
                        
                    

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    department_ids = fields.Many2many(
        'hr.department',
        string="Departments",
        required=False,
        default=lambda self: self.env.user.employee_id.department_id
    )