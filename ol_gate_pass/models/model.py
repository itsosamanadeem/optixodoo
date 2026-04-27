from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class GatePass(models.Model):
    _name = "gate.pass"
    _inherit = ["mail.thread", "mail.activity.mixin"]


    def unlink(self):
        """
        Override the unlink method to add custom logic before deletion.
        """
        for rec in self:
            # If the record's state is 'posted', raise an error to prevent deletion
            if rec.state == 'posted':
                raise UserError("You cannot delete a record that is in the 'posted' state.")

        # If the logic passes (i.e., no error raised), proceed with the deletion
        return super(GatePass, self).unlink()
 
 
    invoice_names = fields.Char(string="Invoice Names", compute="_compute_invoice_names")
    grn_count=fields.Integer('GRN Count',compute='_compute_grn_count')
    edit=fields.Boolean('Edit',default=True)

    def _compute_grn_count(self):
        for rec in self :
            if rec.grn_document_id:
                rec.grn_count=len(rec.grn_document_id)
            else:
                rec.grn_count=0

    def action_open_picking(self):
        for record in self:
            if record.grn_document_id:
                # Opens the Sale Order form and tree view
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Grn Documents',
                    'res_model': 'stock.picking',
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', record.grn_document_id.ids)],
                    'target': 'current',
                }

    def _compute_invoice_names(self):
     for gate_pass in self:
        invoice_names = []
        # Check all GRN documents (pickings) linked to this gate pass
        for picking in gate_pass.grn_document_id:
            # Case 1: If picking is linked to a sale order (for outgoing shipments)
            if picking.sale_id and picking.sale_id.invoice_ids:
                invoice_names.extend(picking.sale_id.invoice_ids.mapped('name'))
            # Case 2: If picking is linked to a purchase order (for incoming shipments)
            elif picking.purchase_id and picking.purchase_id.invoice_ids:
                invoice_names.extend(picking.purchase_id.invoice_ids.mapped('name'))
        # Join all invoice names (remove duplicates)
        gate_pass.invoice_names = ", ".join(set(filter(None, invoice_names)))

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, string="Company")

    name = fields.Char(copy=False, default='New')
    origin = fields.Char(string="PO No.", compute="_compute_origin", store=True)

    gate_pass_type = fields.Selection(selection=[
        ('gate_in', 'Gate IN'),
        ('gate_out', 'Gate OUT'),
        ('rgp', 'Returnable Gate Pass'),
    ], string="Gate Type", required=True)
    

 
    
    grn_document_id = fields.Many2many(
        'stock.picking',
        string="GRN Document",
    )
    
    picking_ids = fields.One2many('stock.picking', string="Picking Ids", compute="_compute_picking_ids")
  
    expected_return_date = fields.Date(string="Expected Return Date")
    actual_return_date = fields.Date(string="Actual Return Date")
    return_reason = fields.Selection([
        ('repair', 'Repair'),
        ('testing', 'Testing'),
        ('sample', 'Sample'),
        ('other', 'Other')
    ], string="Reason for Return")
    return_status = fields.Selection([
        ('pending', 'Pending'),
        ('returned', 'Returned'),
        ('done', 'Done'),
    ], string="Return Status", default='pending', tracking=True)

    vendor_id = fields.Many2many('res.partner', string="Partner")
    vendor_ids = fields.One2many('res.partner', string="Vendor Ids", compute="_compute_vendor_ids")

    truck_no = fields.Char(string="Truck No")
    receiver = fields.Char(string="Receiver")
    date_start = fields.Datetime(
        string="Creation date",
        default=fields.Datetime.now(),
        readonly=True
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    pass_date = fields.Datetime(string='Pass Date', required=True)
    gate_pass_ids = fields.One2many('gate.pass.line', 'gate_pass_id', string="Gate Pass Lines")
    product_ids = fields.Many2many('product.product', string="Products", compute="_compute_product_ids")

    @api.depends('gate_pass_ids')
    def _compute_product_ids(self):
        for rec in self:
            products = rec.gate_pass_ids.mapped('product_id')
            rec.product_ids = products

    @api.depends('grn_document_id')
    def _compute_origin(self):
        """
        Compute the origin field from the first GRN document (stock.picking).
        """
        for rec in self:
            if rec.grn_document_id:
                rec.origin = rec.grn_document_id[0].origin
            else:
                rec.origin = False

    @api.depends('gate_pass_type')
    def _compute_vendor_ids(self):
        for rec in self:
            vendors = self.env['res.partner']
            if rec.gate_pass_type == 'gate_in':
                vendors = self.env['res.partner'].search([('supplier_rank', '>', 0)])
            elif rec.gate_pass_type == 'gate_out':
                vendors = self.env['res.partner'].search([('customer_rank', '>', 0)])
            elif rec.gate_pass_type == 'rgp':
                vendors = self.env['res.partner'].search(['|', ('supplier_rank', '>', 0), ('customer_rank', '>', 0)])
            rec.vendor_ids = vendors

    @api.depends('gate_pass_type')
    def _compute_picking_ids(self):
        for rec in self:
            if rec.gate_pass_type =='gate_in':
                pickings = self.env['stock.picking'].search([
                    ('state', '=', 'assigned'),('picking_type_id.code', '=', 'incoming')])
                rec.picking_ids=pickings.ids
            else:
                pickings = self.env['stock.picking'].search([
                    ('state', '=', 'done'),('picking_type_id.code', '=', 'outgoing')])
                rec.picking_ids=pickings.ids

    def generate_name(self):
        for rec in self:
            sequence_date = datetime.now()
            month_name = sequence_date.strftime('%B').upper()
            year = sequence_date.strftime('%Y')

            if rec.gate_pass_type == 'gate_in' and rec.name == 'New':
                sequence = self.env['ir.sequence'].next_by_code('gate.pass.in.sequence') or 'New'
                rec.name = sequence

            elif rec.gate_pass_type == 'gate_out' and rec.name == 'New': 
                sequence = self.env['ir.sequence'].next_by_code('gate.pass.out.sequence') or 'New'
                rec.name = sequence


            elif rec.gate_pass_type == 'rgp' and rec.name == 'New':
                sequence = self.env['ir.sequence'].next_by_code('gate.pass.rgp.sequence')
                if not sequence:
                    raise UserError("RGP sequence is missing. Please configure 'gate.pass.rgp.sequence'.")
                rec.name = sequence


    def button_confirm(self):
        for rec in self:
            check=all([line.confirm_quantity !=0 for line in rec.gate_pass_ids])
            if rec.gate_pass_ids and check:
                rec.state = "posted"
                rec.generate_name()
            else:
                raise UserError("Product confirm quantity can't be 0!")

    def button_reset_to_draft(self):
        for rec in self:
            rec.state = "draft"
            rec.edit=True

    def button_edit(self):
        for rec in self:
            group = self.env['res.groups'].search([('name', '=', 'Gate Pass Edit Approval')], limit=1)
            if group.user_ids:
                for user in group.user_ids:
                    self.create_activity(user.id)
            rec.edit=False

    def create_activity(self, user):
        activity_values = {
            'display_name': 'Gate Pass Edit Approval',
            'summary': 'Gate Pass Edit Approval',
            'date_deadline': datetime.now(),
            'user_id': user,
            'res_id': self.id,
            'res_model_id': self.env['ir.model']._get('gate.pass').id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
        }
        self.env['mail.activity'].create(activity_values)

  

    @api.onchange('grn_document_id')
    def onchange_grn_document_id(self):
        for rec in self:
            if rec.grn_document_id:
                # rec.purchase_request_id = False
                rec.vendor_id = [(5, 0, 0)]
                vendor_ids = []
                for vendor in rec.grn_document_id:
                    if vendor.partner_id:
                        vendor_ids.append((4, vendor.partner_id.id, False))
                rec.vendor_id = vendor_ids
                
                # Clear existing lines
                rec.gate_pass_ids = [(5, 0, 0)]
                for grn_document in rec.grn_document_id:
                    # Add new lines
                    for line in grn_document.move_ids:
                        rec.gate_pass_ids = [(0, 0, {
                            'product_id': line.product_id.id,
                            'description': line.description_picking,
                            'quantity': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                        })]

    @api.constrains('vendor_id')
    def _onchange_vendor_id(self):
        for rec in self:
            if len(rec.vendor_id.ids) > 1:
                raise UserError("Only one vendor allowed on a single gate pass!")

    def action_mark_as_returned(self):
        for rec in self:
            if rec.gate_pass_type == 'rgp' and rec.return_status == 'pending':
                rec.return_status = 'returned'
                rec.actual_return_date = fields.Date.today()
            else:
                raise UserError("You can only mark an RGP with pending status as Returned.")

    def action_mark_as_done(self):
        for rec in self:
            if rec.gate_pass_type == 'rgp' and rec.return_status == 'returned':
                rec.return_status = 'done'
            else:
                raise UserError("You can only mark an RGP with returned status as Done.")



class GatePassLine(models.Model):
    _name = 'gate.pass.line'

    gate_pass_id = fields.Many2one('gate.pass', string="Gate Pass")
    product_id = fields.Many2one('product.product', string="Product")
    other_item = fields.Char(string='Other Item')
    description = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity")
    confirm_quantity = fields.Float(string="Confirm Quantity")
    remarks = fields.Char(string='Remarks')
    product_uom = fields.Many2one('uom.uom', string="Unit")

    @api.onchange('confirm_quantity')
    def onchange_confirm_quantity(self):
        for rec in self:
            if rec.other_item and not rec.product_id:
                rec.quantity = rec.confirm_quantity


class StockPickingInherited(models.Model):
    _inherit = 'stock.picking'

    gate_pass = fields.Char(string="Gate Pass", compute="_compute_gate_pass")
    gate_pass_ids = fields.One2many(
        'gate.pass',
        'grn_document_id',
        string="Gate Passes",
    )

    gate_pass_count=fields.Integer('Gate Pass',compute='_compute_gate_pass_count')

    def _compute_gate_pass_count(self):
        for rec in self :
            if rec.gate_pass_ids:
                rec.gate_pass_count=len(rec.gate_pass_ids)
            else:
                rec.gate_pass_count=0

    def _compute_gate_pass(self):
        for rec in self:
            rec.gate_pass = None
            if not isinstance(rec.id, int):
                continue
            gate_pass_id = self.env['gate.pass'].search([('grn_document_id', 'in', [rec.id])], limit=1)
            if gate_pass_id:
                rec.gate_pass = gate_pass_id.name

    def action_open_gatepass(self):
        for record in self:
            if record.gate_pass_ids:
                # Opens the Sale Order form and tree view
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Grn Documents',
                    'res_model': 'gate.pass',
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', record.gate_pass_ids.ids)],
                    'target': 'current',
                }

    def button_validate(self):
        # for rec in self:
        #     if rec.company_id.id != 2:
        #         if rec.picking_type_id.name in ['Receipts']:
        #             if not rec.gate_pass_ids:
        #                 raise UserError("At least one Gate Pass is required before Validation!")
        #    M.Dawood Zahid 36393         
        return super(StockPickingInherited, self).button_validate()







