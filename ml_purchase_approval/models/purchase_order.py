from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_group_id = fields.Many2one(
        'ml.approval.group',
        string='Approval Group',
        tracking=True
    )
    current_approval_level_id = fields.Many2one(
        'ml.approval.level',
        string='Current Approval Level',
        tracking=True
    )

    approval_history_ids = fields.One2many(
        'ml.approval.history',
        'purchase_order_id',
        string='Approval History'
    )
    requires_approval = fields.Boolean(
        string='Requires Approval',
        compute='_compute_requires_approval',
        store=True
    )

    show_recommend_button = fields.Boolean(
        string='Show Recommend Button',
        compute='_compute_show_recommend_button',
        store=False
    )

    show_returned_button = fields.Boolean(
        string='Show Returned Button',
        compute='_compute_show_returned_button',
        store=False
    )

    show_approval_button = fields.Boolean(
        string='Show Approval Button',
        compute='_compute_show_approval_button',
        store=False
    )

    curr_pending_at_user_show = fields.Char(
        string='Pending At',
        compute='_compute_curr_pending_at_user_show',
        store=False
    )

    def _compute_show_recommend_button(self):
        for order in self:
            show_recommend_button = False
            line = order.current_approval_level_id or False
            if line and  line.is_recommendation and line.active and self.env.user.id in line.user_ids.ids:
                    show_recommend_button = True
            order.show_recommend_button = show_recommend_button


    def _compute_show_returned_button(self):
        for order in self:
            show_returned_button = False
            line = order.current_approval_level_id or False
            if line and  (line.is_recommendation or line.is_approval) and line.active and self.env.user.id in line.user_ids.ids:
                    show_returned_button = True
            order.show_returned_button = show_returned_button


    def _compute_show_approval_button(self):
        for order in self:
            show_approval_button = False
            line = order.current_approval_level_id or False
            if line and line.is_approval and line.active  and self.env.user.id in line.user_ids.ids and order.amount_total <= line.max_amount:
                    show_approval_button = True
            order.show_approval_button = show_approval_button

    def _compute_curr_pending_at_user_show(self):
        for order in self:
            curr_pending_at_user_show = ''
            line = order.current_approval_level_id or False
            if order.state == 'to approve':

                if line and line.active:
                    for user in line.user_ids:
                        curr_pending_at_user_show += user.name+' ['+ ('R' if line.is_recommendation else '') + ('A' if line.is_approval and order.amount_total <= line.max_amount else '') + '], '

                if len(curr_pending_at_user_show) == 0:
                    curr_pending_at_user_show = 'No user attached with this level of approval. Please attach the users in approval group!'

            order.curr_pending_at_user_show = curr_pending_at_user_show


    @api.depends('amount_total', 'approval_group_id', 'state')
    def _compute_requires_approval(self):
        for order in self:
            order.requires_approval = bool(
                order.approval_group_id and
                order.amount_total > 0 and
                order.state in ['draft', 'sent', 'to approve']
            )

    def button_approve(self, force=False):
        # Process orders that are in approval workflow
        orders_with_approval = self.filtered(lambda o: o.current_approval_level_id)

        for order in orders_with_approval:
            # Create approval history record
            self.env['ml.approval.history'].create({
                'purchase_order_id': order.id,
                'approval_level_id': order.current_approval_level_id.id,
                'action': 'approved',
                'user_id': self.env.user.id,
                'notes': "Approved"
            })

        # Call the parent method with the force parameter
        return super(PurchaseOrder, self).button_approve(force=force)


    def button_confirm(self):
        # Override the standard confirm button
        for order in self:
            if order.requires_approval and order.state in ['draft', 'sent']:
                # Instead of confirming, request approval
                return order.action_request_approval()

        # If no approval needed, proceed with standard confirmation
        return super(PurchaseOrder, self).button_confirm()


    def action_request_approval(self):
        self.ensure_one()
        if not self.approval_group_id:
            raise UserError('Please select an approval group first!')

        # Find the first approval level that matches the amount
        approval_level = self._get_next_approval_level()
        if not approval_level:
            # No approval required, confirm directly
            return super(PurchaseOrder, self).button_confirm()

        self.write({
            'state': 'to approve',
            'current_approval_level_id': approval_level.id
        })

        # Create approval history record with comments
        self.env['ml.approval.history'].create({
            'purchase_order_id': self.id,
            'approval_level_id': approval_level.id,
            'action': 'requested',
            'user_id': self.env.user.id,
            'notes': f"Request Created"
        })


    def action_button_next_level(self):
        self.ensure_one()
        if not self.approval_group_id:
            raise UserError('Please select an approval group first!')

        approval_level = self._get_next_approval_level()
        if not approval_level:
            raise UserError('Next Recommendation Level Not Set!')

        # Open wizard instead of directly updating
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Comments',
            'res_model': 'ml.approval.comment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
                'default_approval_level_id': approval_level.id,
            }
        }



    def action_button_prev_level(self):
        self.ensure_one()
        if not self.approval_group_id:
            raise UserError('Please select an approval group first!')

        approval_level = self._get_prev_approval_level()
        if not approval_level:
            raise UserError('Previous Recommendation Level Not Set!')

        # Open wizard instead of directly updating
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Comments',
            'res_model': 'ml.returned.comment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
                'default_approval_level_id': approval_level.id,
            }
        }



    def _get_next_approval_level(self):
        if not self.approval_group_id:
            return False

        # Get all active levels for the group, ordered by sequence
        levels = self.approval_group_id.level_ids.filtered(
            lambda l: l.active
        ).sorted('sequence')

        # for level in levels:
        #     if self.amount_total >= level.min_amount and self.amount_total <= level.max_amount:
        #         return level
        if self.current_approval_level_id:
            for level in levels:
                if level.sequence > self.current_approval_level_id.sequence:
                    return level
        else:
            return levels[0]

        return False

    def _get_prev_approval_level(self):
        if not self.approval_group_id:
            return False

        # Get all active levels for the group, ordered by sequence
        levels = self.approval_group_id.level_ids.filtered(
            lambda l: l.active
        ).sorted('sequence', reverse=True)

        if self.current_approval_level_id:
            for level in levels:
                if level.sequence < self.current_approval_level_id.sequence:
                    return level
        else:
            return levels[0]

        return False


class ApprovalHistory(models.Model):
    _name = 'ml.approval.history'
    _description = 'Approval History'
    _order = 'create_date desc'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='cascade'
    )
    approval_level_id = fields.Many2one(
        'ml.approval.level',
        string='Approval Level',
        required=True
    )
    action = fields.Selection([
        ('requested', 'Approval Requested'),
        ('recommended', 'Recommended'),
        ('returned', 'Returned'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Action', required=True)
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True
    )
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now
    )
    notes = fields.Text(string='Notes')