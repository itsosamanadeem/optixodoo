from re import match
from odoo import models, fields, api, _ #type: ignore
from odoo.exceptions import UserError, ValidationError #type: ignore
from odoo.tools.float_utils import float_compare #type: ignore

class PurchaseOrder(models.Model):
    _name="purchase.order"
    _inherit = ["purchase.order",'mail.thread', 'mail.activity.mixin']

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        required=False,
        default=lambda self: self.env.user.employee_id.department_id
    )
    is_sent_back = fields.Boolean(string="Sent Back", default=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Some flows (e.g. approvals→purchase bridges / custom code) can create a PO without
        # explicitly passing `currency_id`. Purchase Orders require a currency, so ensure
        # it is always populated from the selected company (or current env company).
        for vals in vals_list:
            if not vals.get('currency_id'):
                company_id = vals.get('company_id') or self.env.company.id
                company = self.env['res.company'].browse(company_id)
                vals['currency_id'] = company.currency_id.id
        return super().create(vals_list)

    def write(self, vals):
        # If a record somehow ends up without currency (or company changes), re-apply a default.
        if ('currency_id' in vals and not vals.get('currency_id')) or ('company_id' in vals and 'currency_id' not in vals):
            for order in self:
                currency_id = vals.get('currency_id')
                if not currency_id:
                    company = self.env['res.company'].browse(vals.get('company_id') or order.company_id.id or self.env.company.id)
                    currency_id = company.currency_id.id
                # Only set if needed; avoid unnecessary writes.
                if not vals.get('currency_id') and not order.currency_id:
                    vals = dict(vals, currency_id=currency_id)
                    break
        return super().write(vals)
    
    def action_button_next_level(self):
        res = super().action_button_next_level()

        activity_type = self.env.ref('mail.mail_activity_data_todo')
        model_id = self.env['ir.model']._get('purchase.order').id

        for order in self:
            approval_level = order._get_next_approval_level()
            if not approval_level:
                continue

            users = approval_level.user_ids.filtered(lambda u: u)

            activities_vals = []
            for user in users:
                activities_vals.append({
                    'activity_type_id': activity_type.id,
                    'summary': 'Purchase Order Recommendation Required',
                    'note': f'Please review and recommend PO {order.name}',
                    'user_id': user.id,
                    'res_id': order.id,
                    'res_model_id': model_id,
                })

            if activities_vals:
                self.env['mail.activity'].create(activities_vals)

        return res
        
    def action_button_prev_level(self):
        self.ensure_one()

        if not self.approval_group_id:
            raise UserError('Please select an approval group first!')

        approval_level = self._get_prev_approval_level()
        if not approval_level:
            raise UserError('Previous Recommendation Level Not Set!')

        # Get SCM users
        scm_group = self.env.ref('purchase_inherit.group_scm_user')
        scm_users = scm_group.user_ids

        # Users in approval level
        level_users = approval_level.user_ids

        # ✅ Intersection (THIS is what you need)
        matched_users = level_users & scm_users

        if not matched_users:
            raise UserError('No SCM user found in this approval level!')

        # (Optional) create activities only for matched users
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        model_id = self.env['ir.model']._get('purchase.order').id

        activities_vals = []
        for user in matched_users:
            activities_vals.append({
                'activity_type_id': activity_type.id,
                'summary': 'Purchase Order Returned',
                'note': f'PO {self.name} requires your review again',
                'user_id': user.id,
                'res_id': self.id,
                'res_model_id': model_id,
            })

        if activities_vals:
            self.env['mail.activity'].create(activities_vals)

        # ✅ Pass correct level
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
    
    def button_draft(self):
        res = super().button_draft()
        for rec in self:
            rec.current_approval_level_id = None
        return res
        
    def button_confirm(self):
        for order in self:
            ctx = dict(self.env.context)
            if order.state == 'draft':
                ctx.update({'skip_budget_check': True})

            order = order.with_context(ctx)
            
            if not order.order_line:
                raise UserError(_("Please add at least one line to confirm the purchase order."))

            managers = self.env['res.users']
            for line in order.order_line:
                if line.department_id:
                    managers |= line.department_id.mapped('manager_id.user_id').filtered(lambda u:u)
            
            if order.is_sent_back and line.amount_to_change: #type:ignore
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
        return super(PurchaseOrder, self.with_context(ctx)).button_confirm() #type:ignore
    
    def button_approve(self):
        if self.env.context.get('skip_budget_check'):
            return super().button_approve()
        
        for order in self:
            # budget logic per line
            for line in order.order_line:
                if not line.department_id or not line.department_id.analytic_city_id:
                    raise UserError(_(
                        "Please set an analytic account for department '%s'."
                    ) % (line.department_id.name or 'Unknown'))
                
                if not line.product_id.analytic_gl_id:
                    raise UserError(_(
                        "Please set analytic GL for this product '%s'."
                    )% (line.product_id.analytic_gl_id))
                ac = self.env['budget.line'].sudo().search([
                    ('account_id', '=', line.department_id.analytic_account_id.id),
                    ('x_plan10_id','=',line.product_id.analytic_gl_id),
                    ('budget_analytic_id.state','=','done')
                ], limit=1)
                # raise UserError(_("Analytic Account: %s") % ac.b)
                if not ac or not ac.budget_analytic_id:
                    raise UserError(_(
                        "No budget configuration found for the analytic account '%s'."
                    ) % line.department_id.analytic_account_id.name)
                configuration = ac.budget_analytic_id.sudo().configuration
                
                if configuration == 'restrict':
                    if ac.budget_amount < line.price_subtotal:
                        raise ValidationError(_(
                            "The total amount of the purchase order exceeds the available budget "
                            "for the department '%s'."
                        ) % line.department_id.name)
                elif configuration == 'warning':
                    if ac.budget_amount < line.price_subtotal:
                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'Budget Warning',
                            'res_model': 'budget.warning.wizard',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_order_id': order.id,
                                'default_message': _(
                                    "Budget exceeded for department '%s'.\n\n"
                                    "Available Budget: %s\n"
                                    "PO Amount: %s\n\n"
                                    "Do you want to proceed?"
                                ) % (
                                    line.department_id.name,
                                    ac.budget_amount,
                                    order.amount_total
                                )
                            }
                        }
                    else:
                        self._post_budget_warning_actions()
                elif configuration == 'allow':
                    self._post_budget_warning_actions()
                    continue
                
        return super().button_approve()
    
    def _post_budget_warning_actions(self):
        self.ensure_one()

        levels = self.approval_group_id.level_ids
        dept_managers = self.order_line.mapped('department_id.manager_id.user_id')

        filtered_levels = levels.filtered(
            lambda l: set(l.user_ids.ids) & set(dept_managers.ids)
        )

        filtered_levels.sudo().write({'active': False})

        partners = dept_managers.mapped('partner_id')
        partners |= self.create_uid.partner_id

        self.message_post(
            body=_("Purchase Order Approved with Budget Warning"),
            partner_ids=partners.ids,
            subtype_xmlid='mail.mt_note'
        )
        self.button_lock()