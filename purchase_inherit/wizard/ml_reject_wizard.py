from odoo import models, fields, api
from odoo.exceptions import UserError

class ReturnedCommentWizard(models.TransientModel):
    _inherit = 'ml.returned.comment.wizard'
    
    def action_confirm_with_comment(self):
        super(ReturnedCommentWizard, self).action_confirm_with_comment()
        self.ensure_one()
        if not self.comment:
            raise UserError('Please enter comments before proceeding.')
        order = self.purchase_order_id
        order.write({
            'is_sent_back': True,
            'state': 'draft',
            'current_approval_level_id': False
        })
        return {'type': 'ir.actions.act_window_close'}