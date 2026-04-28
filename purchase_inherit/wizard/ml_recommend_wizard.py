from odoo import models, fields, api
from odoo.exceptions import UserError


class ApprovalCommentWizardInherit(models.TransientModel):
    _inherit = 'ml.approval.comment.wizard'
    _description = 'Approval Comment Wizard'

    def action_confirm_with_comment(self):
        super(ApprovalCommentWizardInherit, self).action_confirm_with_comment()
        order = self.purchase_order_id
        managers = order._get_department_managers()
        lines_with_change = order.order_line.filtered(lambda l: l.amount_to_change)

        if managers and lines_with_change:
            order.is_sent_back = True
            activity_type = self.env.ref('mail.mail_activity_data_todo')

            for user in managers:
                model_id = self.env['ir.model']._get('purchase.order').id
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': 'Purchase Order Returned',
                    'note': f'PO {order.name} requires your review again',
                    'user_id': user.id,
                    'res_id': order.id,
                    'res_model_id': model_id,
                })
        return {'type': 'ir.actions.act_window_close'}