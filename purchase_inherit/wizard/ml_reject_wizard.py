from odoo import models, fields, api #type:ignore
from odoo.exceptions import UserError #type:ignore

class ReturnedCommentWizard(models.TransientModel):
    _inherit = 'ml.returned.comment.wizard'
    
    def action_confirm_with_comment(self):
        super(ReturnedCommentWizard, self).action_confirm_with_comment()
        self.ensure_one()
        if not self.comment:
            raise UserError('Please enter comments before proceeding.')
        order = self.purchase_order_id
        managers = order._get_department_managers()
        order.write({
            'is_sent_back': True,
            'department_manager_ids': [(6, 0, managers.ids)],
            'department_manager_approved_ids': [(5, 0, 0)]
        })
        
        return {'type': 'ir.actions.act_window_close'}