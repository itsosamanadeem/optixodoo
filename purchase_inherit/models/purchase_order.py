from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

class PurchaseOrder(models.Model):
    _inherit = ["purchase.order",'mail.thread', 'mail.activity.mixin']

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        required=False,
        default=lambda self: self.env.user.employee_id.department_id
    )
    is_sent_back = fields.Boolean(string="Sent Back", default=False, readonly=True)
    
    def action_button_prev_level(self):
        for order in self:
            order.button_unlock()
            # Activity
            group = self.env.ref('purchase_inherit.group_scm_user')
            scm_users = group.user_ids
            # scm_users = self.env['res.users'].search([('groups_id', 'in', self.env.ref('purchase_inherit.group_scm_user').id)])
            for user in scm_users:
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': _('Purchase Order Confirmation'),
                    'user_id': user.id,
                    'res_id': order.id,
                    'res_model_id': self.env['ir.model']._get('purchase.order').id,
                })
        return super().action_button_prev_level()
            
    def button_confirm(self):
        for order in self:
            if not order.order_line:
                raise UserError(_("Please add at least one line to confirm the purchase order."))

            managers = self.env['res.users']
            for line in order.order_line:
                if line.department_ids:
                    managers |= line.department_ids.mapped('manager_id.user_id').filtered(lambda u:u)
            
            # raise UserError(_("Managers: %s") % managers.mapped('name'))
            if order.is_sent_back and line.amount_to_change:
                for manager in managers:
                    if not manager:
                        raise UserError(_("A department manager has no linked user."))
                    
                    approval_level = self.env['ml.approval.level']

                    existing_levels = approval_level.search([
                        ('group_id', '=', order.approval_group_id.id)
                    ], order="sequence asc")
                    
                    # raise UserError(_("Existing Levels: %s") % existing_levels.mapped('name'))
                    existing_manager_levels = approval_level.with_context(active=False).search([
                        ('group_id', '=', order.approval_group_id.id),
                        ('user_ids', 'in', managers.ids)
                    ])
                    if existing_manager_levels:
                        existing_manager_levels.sudo().write({
                            'active':True
                        })
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
            order.button_lock()
        return super().button_confirm()
    
    def button_approve(self):
        for order in self:
            levels = order.approval_group_id.level_ids
            dept_managers = order.order_line.mapped('department_ids.manager_id.user_id')
            filtered_levels = levels.filtered(lambda l: set(l.user_ids.ids) & set(dept_managers.ids))
            filtered_levels.sudo().write({'active': False})
            partners = dept_managers.mapped('partner_id')
            partners |= order.create_uid.partner_id
            # raise UserError(_("Filtered Levels: %s") % partners.mapped('name'))
            order.message_post(
                body=_("Purchase Order Approved"),
                partner_ids=partners.ids,
                subtype_xmlid='mail.mt_note'
            )
            order.button_lock()
        return super().button_approve()
            # raise UserError(_("Filtered Levels: %s") % filtered_levels.mapped('name'))
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    department_ids = fields.Many2many(
        'hr.department',
        string="Departments",
        required=False,
    )
    
    amount_to_change = fields.Float(string="Amount to Change")
    
    # @api.depends('product_qty', 'price_unit', 'tax_ids', 'discount','amount_to_change')
    # def _compute_amount(self):
    #     super()._compute_amount()
    #     for line in self:
    #         line.price_total += line.amount_to_change

    @api.depends('product_qty', 'product_uom_id', 'company_id', 'order_id.partner_id', 'amount_to_change')                        
    def _compute_price_unit_and_date_planned_and_name(self):
        super()._compute_price_unit_and_date_planned_and_name()
        for line in self:
            if line.amount_to_change:
                line.price_unit += line.amount_to_change       
            line.price_tax += line.amount_to_change