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

            for line in order.order_line:
                if line.department_ids:
                    managers = line.department_ids.mapped('manager_id.user_id')

                    for manager in managers:
                        if not manager:
                            raise UserError(_("A department manager has no linked user."))

                        for level in order.approval_group_id.level_ids:
                            if manager.id not in level.user_ids.ids:
                                level.write({
                                    'user_ids': [(4, manager.id)]
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