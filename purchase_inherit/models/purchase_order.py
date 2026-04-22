from re import match

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
    
    def action_button_prev_level(self):
        for order in self:
            order.button_unlock()
            group = self.env.ref('purchase_inherit.group_scm_user')
            scm_users = group.user_ids
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
        return super(PurchaseOrder, self.with_context(ctx)).button_confirm()
    
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
                ac = self.env['budget.line'].sudo().search([
                    ('account_id', '=', line.department_id.analytic_account_id.id),
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
                elif configuration == 'allow':
                    continue

            # 📧 Email Notification Logic
            levels = order.approval_group_id.level_ids
            dept_managers = order.order_line.mapped('department_id.manager_id.user_id')
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