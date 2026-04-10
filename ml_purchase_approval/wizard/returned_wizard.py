from odoo import models, fields, api
from odoo.exceptions import UserError


class ReturnedCommentWizard(models.TransientModel):
    _name = 'ml.returned.comment.wizard'
    _description = 'Returned Comment Wizard'

    comment = fields.Text(string='Comments', required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    approval_level_id = fields.Many2one('ml.approval.level', string='Approval Level')

    def action_confirm_with_comment(self):
        self.ensure_one()
        if not self.comment:
            raise UserError('Please enter comments before proceeding.')

        # Update the purchase order with the next level
        self.purchase_order_id.write({
            'current_approval_level_id': self.approval_level_id.id
        })

        # Create approval history record with comments
        self.env['ml.approval.history'].create({
            'purchase_order_id': self.purchase_order_id.id,
            'approval_level_id': self.approval_level_id.id,
            'action': 'returned',
            'user_id': self.env.user.id,
            'notes': f"Comments: {self.comment}"
        })

        return {'type': 'ir.actions.act_window_close'}