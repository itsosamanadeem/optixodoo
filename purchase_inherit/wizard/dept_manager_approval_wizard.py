from odoo import models, fields, api, _ #type:ignore
from odoo.exceptions import UserError #type:ignore

class DeptManagerApprovalWizard(models.TransientModel):
    _name = 'dept.manager.approval.wizard'
    _description = 'Department Manager Approval'

    purchase_order_id = fields.Many2one('purchase.order')
    po_name = fields.Char(readonly=True)
    comment = fields.Text()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        po_id = self.env.context.get('default_purchase_order_id')
        if po_id:
            po = self.env['purchase.order'].sudo().browse(po_id)
            res['po_name'] = po.name

        return res

    def action_approve(self):
        self.ensure_one()

        order = self.purchase_order_id.sudo()

        if self.env.user not in order.department_manager_ids:
            raise UserError("You are not allowed to approve this.")

        order.write({
            'department_manager_approved_ids': [(4, self.env.user.id)]
        })

        # mark activity done
        activities = self.env['mail.activity'].sudo().search([
            ('res_id', '=', order.id),
            ('user_id', '=', self.env.user.id),
            ('res_model', '=', 'purchase.order')
        ])
        activities.action_done()