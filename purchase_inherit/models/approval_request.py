from collections import defaultdict

from odoo import models, fields,api, _ #type:ignore
from odoo.exceptions import UserError #type:ignore
from odoo.tools import html_escape #type:ignore
import json
import logging
_logger = logging.getLogger(__name__)

class ApprovalForm(models.Model):
    _inherit = 'approval.request'

    amount = fields.Float( string="Amount",compute="_compute_amount",readonly=True, store=True)
    request_type = fields.Selection([
        ('pr', 'Purchase Request'),
        ('ir', 'Internal Request'),
        ('pc', 'Petty Cash'),
        ], default='pr', required=True, index=True)
    
    request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('partial_approved', 'Partial Approved'),
        ('purchase_order_created', 'Purchase Order Created'),
        ('internal_transfer_created', 'Internal Transfer Created'),
        ('refused', 'Refused'),
        ('cancel', 'Canceled'),
    ], default="new", compute="_compute_request_status",
        store=True, index=True, tracking=True,
        group_expand=True)
    
    @staticmethod
    def _line_qty(line):
        return line.po_uom_qty or line.quantity or 0.0

    def _get_current_user_approver(self):
        approvers = self.env['approval.approver']
        status_priority = ('pending', 'waiting', 'new', 'approved', 'refused', 'cancel')
        for request in self:
            user_approvers = request.approver_ids.filtered(
                lambda approver: approver.user_id == self.env.user
            )
            for status in status_priority:
                approver = user_approvers.filtered(lambda line: line.status == status)[:1]
                if approver:
                    approvers |= approver
                    break
        return approvers

    def create_internal_transfers_for_request(self):
        stock_picking = self.env['stock.picking'].sudo()
        picking_type = self.env.ref('stock.picking_type_internal')
        source_location = self.env.ref('stock.stock_location_stock')
        created_transfer_count = 0
        move_field_name = 'move_ids_without_package' if 'move_ids_without_package' in stock_picking._fields else 'move_ids'

        for request in self:
            if request.name in self.env['stock.picking'].sudo().search([('origin', '=', request.name)]).mapped('origin'):
                raise UserError(_("An internal transfer has already been created for this request."))
            transferable_lines = request.product_line_ids.filtered(
                lambda l: (
                    l.product_id
                    and l.product_id.type == 'consu'
                    and not l.manager_refused
                    and l.status != 'refused'
                )
            )
            # raise UserError(str(transferable_lines.mapped('id')))
            lines_by_department = defaultdict(list)
            for line in transferable_lines:
                if not line.department_id:
                    raise UserError(
                        _("Please set a department on approval line '%s' before creating an internal transfer.")
                        % (line.product_id.display_name or line.description or request.name)
                    )
                if not line.department_id.location_id:
                    raise UserError(
                        _("Please configure a department stock location for '%s' before creating an internal transfer.")
                        % line.department_id.display_name
                    )
                qty = self._line_qty(line)
                if qty <= 0:
                    continue
                lines_by_department[(line.company_id.id, line.department_id.id)].append(line)

            for (_company_id, _department_id), department_lines in lines_by_department.items():
                department = department_lines[0].department_id
                manager_partner = department.manager_id.user_id.partner_id
                picking_vals = {
                    'origin': request.name,
                    'partner_id': manager_partner.id if manager_partner else False,
                    'picking_type_id': picking_type.id,
                    'location_id': source_location.id,
                    'location_dest_id': department.location_id.id,
                    move_field_name: [],
                }
                for line in department_lines:
                    qty = self._line_qty(line)
                    if qty <= 0:
                        continue
                    picking_vals[move_field_name].append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_qty': qty,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': department.location_id.id,
                        'company_id': line.company_id.id,
                    }))
                if picking_vals[move_field_name]:
                    stock_picking.create(picking_vals)
                    created_transfer_count += 1
                request.sudo().write({'request_status': 'internal_transfer_created'})
        return created_transfer_count
    
    @api.depends('product_line_ids', 'product_line_ids.manager_refused', 'request_status')
    def _compute_amount(self):
        for rec in self:
            active_lines = rec.product_line_ids.filtered(lambda l: not l.manager_refused and l.price_unit)
            rec.amount = sum(active_lines.mapped(lambda l: l.price_unit * (l.po_uom_qty or 1)))

    def _promote_next_waiting_approvers(self):
        """Advance approval queue: if no pending approver exists, move next waiting sequence to pending."""
        for request in self:
            approvers = request.approver_ids.sudo()
            if not approvers:
                continue
            if approvers.filtered(lambda a: a.status == 'pending'):
                continue
            waiting = approvers.filtered(lambda a: a.status == 'waiting')
            if not waiting:
                continue
            next_sequence = min(waiting.mapped('sequence'))
            waiting.filtered(lambda a: a.sequence == next_sequence).write({'status': 'pending'})
            
    def action_confirm(self):
        skip_city_check = self.env.context.get('skip_city_check')
        for request in self:
            departments = request.product_line_ids.mapped('department_id')
            approvers_to_add = []
            existing_approver_user_ids = set(request.approver_ids.mapped('user_id').ids)
            for department in departments:
                if not department:
                    continue
                manager_employee = department.manager_id
                if not manager_employee:
                    raise UserError(_("Department '%s' has no manager assigned.") % department.name)
                manager_user = manager_employee.user_id
                if not manager_user:
                    raise UserError(
                        _("Manager '%s' of department '%s' has no linked user.")
                        % (manager_employee.name, department.name)
                    )
                if not skip_city_check and department.analytic_city_id.name == '000':
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'City Warning',
                        'res_model': 'city.warning.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_request_id': request.id,
                            'default_message': _(
                                "City for department '%s'.\n\n"
                                "is: %s\n"
                                "Do you want to proceed?"
                            ) % (
                                department.name,
                                department.analytic_city_id.name,
                            )
                        }
                    }
                if manager_user.id not in existing_approver_user_ids:
                    approvers_to_add.append(manager_user.id)
                    existing_approver_user_ids.add(manager_user.id)
            if approvers_to_add:
                existing_sequences = request.approver_ids.mapped('sequence')
                next_sequence = max(existing_sequences, default=0) + 1
                request.sudo().write({
                    'approver_ids': [
                        (0, 0, {
                            'user_id': uid,
                            'required': True,
                            # Same sequence => all department managers can approve in parallel.
                            'sequence': next_sequence,
                        }) for uid in approvers_to_add
                    ]
                })
            if not request.approver_ids:
                raise UserError(_("You must have at least one approver before confirming."))
            
        return super().action_confirm()

    def action_create_purchase_orders(self):
        sudo_self = self.sudo()
        res = super(ApprovalForm, sudo_self).action_create_purchase_orders()
        self.sudo().write({
            'request_status': 'purchase_order_created'
            })
        sudo_self._create_activity()
        sudo_self._send_po_approval_email_to_scm()
        if self.env.user.has_group('purchase_inherit.group_scm_user'):
            for rec in self:
                rec._mark_scm_activities_done()
                
        return res

    def action_draft(self):
        for request in self:
            # owner_user = False
            # if 'request_owner_id' in request._fields:
            #     owner_user = request.request_owner_id
            # elif 'owner_id' in request._fields:
            #     owner_user = request.owner_id
            # if not owner_user:
            #     owner_user = request.create_uid

            # if (
            #     owner_user
            #     and owner_user != self.env.user
            #     and not self.env.user.has_group('approvals.group_approval_manager')
            # ):
            #     raise UserError(_("Only the requester or an Approval Manager can reset to draft this request."))
            request.product_line_ids.sudo().write({
                'manager_refused': False,
                'manager_refused_by_id': False,
                'manager_refused_date': False,
                'status': 'approved',
            })
            request._compute_amount()
        return super(ApprovalForm, self.sudo()).action_draft()
    
    # def action_cancel(self):
    #     # for request in self:
    #     #     owner_user = False
    #     #     if 'request_owner_id' in request._fields:
    #     #         owner_user = request.request_owner_id
    #     #     elif 'owner_id' in request._fields:
    #     #         owner_user = request.owner_id
    #     #     if not owner_user:
    #     #         owner_user = request.create_uid

    #     #     if (
    #     #         owner_user
    #     #         and owner_user != self.env.user
    #     #         and not self.env.user.has_group('approvals.group_approval_manager')
    #     #     ):
    #     #         raise UserError(_("Only the requester or an Approval Manager can cancel this request."))

    #     return super(ApprovalForm, self.sudo()).action_cancel()
    
    def action_approve(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self._get_current_user_approver()
        res = super().action_approve(approver=approver)
        for request in self:
            if request.product_line_ids.filtered(lambda l: l.manager_refused):
                # If any line is refused by a manager, the request cannot be fully approved.
                request.write({'request_status': 'partial_approved'})
        return res

    @api.depends_context('uid')
    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for approval in self:
            approver = approval._get_current_user_approver()
            approval.user_status = approver.status if approver else False
    
    def _create_purchase_orders(self):
        sudo_self = self.sudo()
        sudo_self.product_line_ids._check_products_vendor()

        po_model = self.env['purchase.order'].sudo()
        po_line_model = self.env['purchase.order.line'].sudo()
        created_po_count = 0

        for request in sudo_self:
            # RFQ grouping rule requested:
            # 1) different products (even same department) => different POs
            # 2) same product + different departments => same PO, separate lines
            # 3) approval product lines stay separate on the PO
            lines_by_po_key = defaultdict(list)
            for line in request.product_line_ids.filtered(lambda l: not l.manager_refused and l.status != 'refused'):
                qty_for_seller = self._line_qty(line) or 1.0
                seller = line.seller_id or line.product_id.with_company(line.company_id)._select_seller(
                    quantity=qty_for_seller,
                    uom_id=line.product_id.uom_id,
                )
                if not seller:
                    continue
                vendor = seller.partner_id
                po_key = (vendor.id, line.company_id.id, line.product_id.id)
                lines_by_po_key[po_key].append((line, seller, vendor))

            for _, packed_lines in lines_by_po_key.items():
                first_line, _, first_vendor = packed_lines[0]
                po_vals = first_line._get_purchase_order_values(first_vendor)
                po_vals['reason'] = request.reason
                purchase_order = po_model.create(po_vals)
                request._copy_attachments_to_purchase_order(purchase_order)
                created_po_count += 1

                for line, seller, _vendor in packed_lines:
                    po_uom_qty = self._line_qty(line) or 0.0
                    po_line_vals = po_line_model._prepare_purchase_order_line(
                        line.product_id,
                        po_uom_qty,
                        seller.product_uom_id,
                        line.company_id,
                        first_vendor,
                        purchase_order,
                    )
                    po_line = po_line_model.create(po_line_vals)
                    po_line.write({
                        'department_id': line.department_id.id,
                        'analytic_distribution': line.analytic_distribution,
                        'price_unit': line.price_unit or 0.0,
                    })
                    line.purchase_order_line_id = po_line.id
                    
        if not created_po_count:
            raise UserError(
                    "No inventory out or purchase order was created. "
                    "Please ensure approved lines have a department, valid quantity, stock availability, "
                    "and a vendor for items that must be purchased."
                )
        return True


    def action_refuse(self, approver=None):
        """
        Department manager refusal only affects that manager's department lines.
        The whole request is refused only if all lines end up refused.
        """
        if not isinstance(approver, models.BaseModel):
            approver = self._get_current_user_approver()
        fully_refused_requests = self.env['approval.request']
        for request in self:
            if request.env.user in request.approver_ids.mapped('user_id'):
                manager_lines = request.product_line_ids.filtered(
                    lambda l: l.department_id.manager_id.user_id == request.env.user
                )
                for line in manager_lines:
                    line.sudo().write({
                        'manager_refused': True,
                        'status': 'refused',
                        'manager_refused_by_id': request.env.user.id,
                        'manager_refused_date': fields.Datetime.now(),
                    })
                approver_line = request.approver_ids & approver
                if not approver_line:
                    approver_line = self.env['approval.approver'].sudo().search([
                        ('user_id', '=', request.env.user.id),
                        ('request_id', '=', request.id)
                    ], limit=1)
                approver_line = approver_line[:1]
                remaining_lines = request.product_line_ids.filtered(lambda l: not l.manager_refused and l.status != 'refused')
                if not remaining_lines:
                    if approver_line:
                        approver_line.sudo().write({'status': 'refused'})
                    fully_refused_requests |= request
                else:
                    # Do not refuse the full request yet; this approver has completed their decision.
                    if approver_line:
                        approver_line.sudo().write({'status': 'approved'})
                    request._promote_next_waiting_approvers()
        # Only run the standard refusal flow for requests where every line is refused.
        if fully_refused_requests:
            return super(ApprovalForm, fully_refused_requests).action_refuse(approver=approver)
        return True

    def action_withdraw(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self._get_current_user_approver()
        return super().action_withdraw(approver=approver)
    
    def _create_activity(self):        
        scm_group = self.env.ref('purchase_inherit.group_scm_user')
        scm_users = scm_group.user_ids
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        model_id = self.env['ir.model']._get('approval.request').id
        for request in self:
            for user in scm_users:
                # Create Activity
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': 'New Purchase Request',
                    'note': f'PR {request.name} requires SCM review',
                    'user_id': user.id,
                    'res_id': request.id,
                    'res_model_id': model_id,
                })
                # Send Email
                # if user.partner_id.email:
                #     request.message_post(
                #         body=f"New Purchase Request {request.name} requires your review.",
                #         partner_ids=[user.partner_id.id],
                #         subtype_xmlid="mail.mt_comment",
                #     )

    def _send_po_approval_email_to_scm(self):
        scm_group = self.env.ref('purchase_inherit.group_scm_user')
        scm_users = scm_group.user_ids.filtered(lambda user: user.partner_id.email)
        if not scm_users:
            return

        for request in self:
            purchase_orders = request.product_line_ids.mapped('purchase_order_line_id.order_id')
            for purchase_order in purchase_orders:
                subject = _("Purchase Order %s Sent for Approval") % purchase_order.name
                body = _(
                    "Purchase Order %(po_name)s has been sent to you for approval from Approval Request %(request_name)s."
                ) % {
                    'po_name': purchase_order.name,
                    'request_name': request.name,
                }
                purchase_order.message_post(
                    body=body,
                    partner_ids=scm_users.mapped('partner_id').ids,
                    subtype_xmlid="mail.mt_comment",
                )
                mail_values = []
                for user in scm_users:
                    mail_values.append({
                        'subject': subject,
                        'body_html': "<p>%s</p>" % html_escape(body),
                        'email_to': user.partner_id.email,
                        'recipient_ids': [(4, user.partner_id.id)],
                        'auto_delete': True,
                    })
                if mail_values:
                    self.env['mail.mail'].sudo().create(mail_values)
    
    def _mark_scm_activities_done(self):
        scm_group = self.env.ref('purchase_inherit.group_scm_user')
        scm_user_ids = scm_group.users.ids

        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'approval.request'),
            ('res_id', '=', self.id),
            ('user_id', 'in', scm_user_ids),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id)
        ])

        activities.action_done()

    def unlink(self):
        locked_statuses = {
            'purchase_order_created',
            'approved',
            'partial_approved',
            'internal_transfer_created',
            'refused',
        }

        locked_requests = self.filtered(lambda request: request.request_status in locked_statuses)
        if locked_requests:
            raise UserError(_(
                "You cannot delete approval requests once their status is Approved, "
                "Partial Approved, Purchase Order Created, Internal Transfer Created, or Refused."
            ))

        return super().unlink()

    def _copy_attachments_to_purchase_order(self, purchase_order):
        self.ensure_one()

        attachment_model = self.env['ir.attachment'].sudo()

        source_attachments = attachment_model.search([
            ('res_model', '=', 'approval.request'),
            ('res_id', '=', self.id),
        ])

        # Also include files attached through chatter messages, if any.
        source_attachments |= self.message_ids.mapped('attachment_ids').sudo()

        if not source_attachments:
            return

        existing_attachments = attachment_model.search([
            ('res_model', '=', 'purchase.order'),
            ('res_id', '=', purchase_order.id),
        ])

        for attachment in source_attachments:
            already_copied = existing_attachments.filtered(
                lambda existing: (
                    existing.name == attachment.name
                    and existing.checksum == attachment.checksum
                )
            )
            if already_copied:
                continue

            attachment.copy({
                'res_model': 'purchase.order',
                'res_id': purchase_order.id,
                'res_field': False,
            })
