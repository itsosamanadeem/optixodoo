# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    reconcile_invoice_ids = fields.One2many('account.payment.reconcile', 'payment_id', string="Invoices", copy=False)
    actual_amount = fields.Float(compute='_compute_actual_amount')

    @api.depends('sales_tds_amt', 'tds_amt', 'amount', 'td_amt')
    def _compute_actual_amount(self):
        for payment in self:
            if payment.wht_type == 'percentage':
                payment.actual_amount = payment.amount - (payment.sales_tds_amt + payment.tds_amt + payment.td_amt)
            else:
                reconcile_payments = self.reconcile_invoice_ids.filtered(lambda x: x.reconcile)
                payment.actual_amount = payment.amount - sum(pmt.it_wht_amt + pmt.st_wht_amt for pmt in reconcile_payments)

    @api.onchange('partner_id', 'payment_type', 'partner_type')
    def _onchange_partner_id(self):
        if not self.partner_id:
            return
        partner_id = self.partner_id
        self.reconcile_invoice_ids = [(5,)]
        move_type = {'outbound': 'in_invoice', 'inbound': 'out_invoice'}
        moves = self.env['account.move'].sudo().search([
            ('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'in_payment']),
            ('move_type', '=', move_type[self.payment_type])
        ])
        vals = []
        for move in moves:
            vals.append((0, 0, {
                'payment_id': self.id,
                'invoice_id': move.id,
                'already_paid': sum([payment['amount'] for payment in move._get_all_reconciled_invoice_partials()]),
                'amount_residual': move.amount_residual,
                'amount_untaxed': move.amount_untaxed,
                'amount_tax': move.amount_tax,
                'currency_id': move.currency_id.id,
                'amount_total': move.amount_total,
            }))
        self.reconcile_invoice_ids = vals
        self.partner_id = partner_id.id
        return

    @api.onchange('reconcile_invoice_ids')
    def _onchnage_reconcile_invoice_ids(self):
        # amount_sum = 0
        # for rec in self.reconcile_invoice_ids:
        #     amount_sum = amount_sum + rec.amount_paid
        #     self.amount = amount_sum
        reconcile_payments = self.reconcile_invoice_ids.filtered(lambda x: x.reconcile)
        self.amount = sum(reconcile_payments.mapped('amount_paid'))
        wht_amount = 0.0
        if self.wht_type == 'percentage':
            wht_amount = sum(record.it_wht_amount + record.st_wht_amount + record.gst_wht_amount for record in reconcile_payments)
        else:
            wht_amount = sum(record.it_wht_amt + record.st_wht_amt for record in reconcile_payments)
        self.actual_amount = self.amount - wht_amount

    # @api.onchange('amount', 'sales_tds_tax_id')
    # def check_amount(self):
    #     for payment in self:
    #         if payment.sales_tds_type == "excluding":
    #             if payment.amount:
    #                 if payment.sales_tds_tax_id:
    #                     payment.sales_tds_amt = payment.amount * (payment.sales_tds_tax_id.amount / 100)
    #         else:
    #             if payment.amount:
    #                 if payment.sales_tds_tax_id:
    #                     payment.sales_tds_amt = payment.amount * (payment.sales_tds_tax_id.amount / 100)

    def action_post(self):
        for payment in self:
            if not payment.name:
                if payment.payment_type == 'inbound':
                    if payment.journal_id.type == 'bank':
                        payment.payment_reference = self.env.ref('dxl_multi_payment_reconciliation.seq_bank_receive_voucher').next_by_id()
                    if payment.journal_id.type == 'cash':
                        payment.payment_reference = self.env.ref('dxl_multi_payment_reconciliation.seq_cash_receive_voucher').next_by_id()
                elif payment.payment_type == 'outbound':
                    if payment.journal_id.type == 'bank':
                        payment.payment_reference = self.env.ref('dxl_multi_payment_reconciliation.seq_bank_payment_voucher').next_by_id()
                    if payment.journal_id.type == 'cash':
                        payment.payment_reference = self.env.ref('dxl_multi_payment_reconciliation.seq_cash_payment_voucher').next_by_id()
            # raise UserError(payment.move_id)
        res = super(AccountPayment, self).action_post()
        # raise UserError(self.move_id)
        # move_lines = self.env['account.move.line']
        # rec_lines = payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile and x.amount_paid > 0)
        # if rec_lines:
        #     for line in rec_lines:
        #         invoice_move = line.invoice_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.account_type in ('payable', 'receivable'))
        #         payment_move = line.payment_id.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.account_type in ('payable', 'receivable'))
        #         move_lines |= (invoice_move + payment_move) 
        #         if invoice_move and payment_move and len(rec_lines) > 1:
        #             if self.partner_type == 'customer':
        #                 rec = self.env['account.partial.reconcile'].with_context(_check_balanced=False).create({
        #                     'amount': abs(line.amount_paid),
        #                     'debit_amount_currency': abs(line.amount_paid),
        #                     'credit_amount_currency': abs(line.amount_paid),
        #                     'debit_move_id': invoice_move.id,
        #                     'credit_move_id': payment_move.id,
        #                     'currency_id':payment.currency_id.id,
        #                 })
        #             else:
        #                 rec = self.env['account.partial.reconcile'].with_context(_check_balanced=False).create({
        #                     'amount': abs(line.amount_paid),
        #                     'debit_amount_currency': abs(line.amount_paid),
        #                     'credit_amount_currency': abs(line.amount_paid),
        #                     'debit_move_id': payment_move.id,
        #                     'credit_move_id': invoice_move.id,
        #                     'currency_id':payment.currency_id.id,
        #                 })
        #     move_lines.filtered(lambda x: not x.reconciled).reconcile()
        return res
    

    # def write(self, vals):
    #     res = super(AccountPayment, self).write(vals)

    #     for payment in self:
    #         if payment.move_id:
    #             # for payment in self:
    #             all_move_vals = payment.move_id.line_ids
    #             if payment.currency_id == payment.company_id.currency_id:
    #                 currency_id = payment.currency_id.id
    #             else:
    #                 currency_id = payment.currency_id.id
    #             tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
    #                 lambda x: x.repartition_type == 'tax')
    #             sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
    #                 lambda x: x.repartition_type == 'tax')
    #             # raise UserError(currency_id)
    #             income_tax_vals = {
    #                 'name': _('Income Tax Withhold'),
    #                 'currency_id': currency_id,
    #                 'for_wht': True,
    #                 'date_maturity': payment.create_date,
    #                 'partner_id': payment.partner_id.id,
    #                 'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id or payment.income_account_id.id,
    #                 'payment_id': payment.id,
    #             }

    #             sales_tax_vals = {
    #                 'name': _('Salse Tax Withhold'),
    #                 'currency_id': currency_id,
    #                 'for_wht': True,
    #                 'date_maturity': payment.create_date,
    #                 'partner_id': payment.partner_id.id,
    #                 'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id or payment.sales_account_id.id,
    #                 'payment_id': payment.id,
    #             }
    #             # raise 
    #             if payment.payment_type == 'outbound':
    #                 debit = 0
    #                 total_credit = 0
    #                 if payment.tds_amt and (payment.tds_type == 'including' or payment.income_account_id):
    #                     credit = payment.tds_amt
    #                     income_tax_vals.update({'credit': credit, 'debit': debit})
    #                     all_move_vals.with_context(check_move_validity=False).update(income_tax_vals)
    #                     total_credit += credit
    #                     # raise UserError(str(all_move_vals))

    #                 if payment.sales_tds_amt and (payment.sales_tds_type == 'including' or payment.sales_account_id):
    #                     credit = payment.sales_tds_amt
    #                     sales_tax_vals.update({'credit': credit, 'debit': debit})
    #                     all_move_vals.with_context(check_move_validity=False).update(sales_tax_vals)
    #                     total_credit += credit

    #                 # Reduce from original credit line
    #                 # if total_credit and all_move_vals:
    #                 #     all_move_vals[0]['credit'] = all_move_vals[0].get('credit', 0) - total_credit
    #                 # debit = 0

    #                 # if payment.tds_amt and (payment.tds_type == 'including' or payment.income_account_id) and payment.sales_tds_type != 'including' and not payment.sales_account_id:
    #                 #     credit = payment.tds_amt
    #                 #     all_move_vals[0]['credit'] = all_move_vals[0]['credit'] - credit
    #                 #     income_tax_vals.update({'credit': credit, 'debit': debit})
    #                 #     all_move_vals.append(income_tax_vals)

    #                 # if payment.sales_tds_amt and (payment.sales_tds_type == 'including' or payment.sales_account_id) and payment.tds_type != 'including' and not payment.income_account_id:
    #                 #     credit = payment.sales_tds_amt
    #                 #     all_move_vals[0]['credit'] = all_move_vals[0]['credit'] - credit
    #                 #     sales_tax_vals.update({'credit': credit, 'debit': debit})
    #                 #     all_move_vals.append(sales_tax_vals)

    #                 # if payment.tds_amt and payment.sales_tds_amt and (payment.sales_tds_type == 'including' or payment.sales_account_id) and (payment.tds_type == 'including' or payment.income_account_id):
    #                 #     credit = payment.sales_tds_amt + payment.tds_amt
    #                 #     all_move_vals[0]['credit'] = all_move_vals[0]['credit'] - credit
    #                 #     income_tax_vals.update({'credit': payment.tds_amt, 'debit': debit})
    #                 #     all_move_vals.append(income_tax_vals)
    #                 #     sales_tax_vals.update({'credit': payment.sales_tds_amt, 'debit': debit})
    #                 #     all_move_vals.append(sales_tax_vals)

    #             if payment.payment_type == 'inbound':
    #                 credit = 0
    #                 total_debit = 0
    #                 if payment.tds_amt and (payment.tds_type == 'including' or payment.income_account_id):
    #                     debit = payment.tds_amt
    #                     income_tax_vals.update({'credit': credit, 'debit': debit})
    #                     all_move_vals.append(income_tax_vals)
    #                     total_debit += debit

    #                 if payment.sales_tds_amt and (payment.sales_tds_type == 'including' or payment.sales_account_id):
    #                     debit = payment.sales_tds_amt
    #                     sales_tax_vals.update({'credit': credit, 'debit': debit})
    #                     all_move_vals.append(sales_tax_vals)
    #                     total_debit += debit

    #                 # Reduce from original debit line
    #                 # if total_debit and all_move_vals:
    #                 #     all_move_vals[0]['debit'] = all_move_vals[0].get('debit', 0) - total_debit

    #                 # raise UserError(res.move_id)
            
    #     return res

    '''def _synchronize_from_moves(self, changed_fields):
        Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1 or len(counterpart_lines) != 1:
                    if self.sales_tds_type == 'default':
                        raise UserError(_(
                            "The journal entry %s reached an invalid state relative to its payment.\n"
                            "To be consistent, the journal entry must always contains:\n"
                            "- one journal item involving the outstanding payment/receipts account.\n"
                            "- one journal item involving a receivable/payable account.\n"
                            "- optional journal items, all sharing the same account.\n\n"
                        ) % move.display_name)

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same currency."
                    ) % move.display_name)

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same partner."
                    ) % move.display_name)

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                liquidity_amount_wht = abs(liquidity_amount)
                if pay.wht_type == 'percentage':
                    liquidity_amount_wht += pay.sales_tds_amt + pay.tds_amt
                else:
                    mv_ids = pay.reconcile_invoice_ids.filtered(lambda x: x.reconcile)
                    liquidity_amount_wht += sum(mv_ids.mapped('it_wht_amt')) + sum(mv_ids.mapped('st_wht_amt'))
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount_wht),
                    'payment_type': 'inbound' if liquidity_amount > 0.0 else 'outbound',
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))'''
    # def _synchronize_to_moves(self, changed_fields):
    #     '''
    #         Update the account.move regarding the modified account.payment.
    #         :param changed_fields: A list containing all modified fields on account.payment.
    #     '''
    #     if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
    #         return

    #     for pay in self:
    #         liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

    #         write_off_line_vals = []
    #         if liquidity_lines and counterpart_lines and writeoff_lines:
    #             write_off_line_vals.append({
    #                 'name': writeoff_lines[0].name,
    #                 'account_id': writeoff_lines[0].account_id.id,
    #                 'partner_id': writeoff_lines[0].partner_id.id,
    #                 'currency_id': writeoff_lines[0].currency_id.id,
    #                 'amount_currency': sum(writeoff_lines.mapped('amount_currency')),
    #                 'balance': sum(writeoff_lines.mapped('balance')),
    #             })

    #         line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

    #         # ================================
    #         # WHT: Adjust liquidity line value
    #         # ================================
    #         if line_vals_list:
    #             # Calculate total liquidity amount based on WHT
    #             liquidity_amount = abs(pay.amount)
    #             if pay.wht_type == 'percentage':
    #                 liquidity_amount += pay.sales_tds_amt + pay.tds_amt
    #             else:
    #                 mv_ids = pay.reconcile_invoice_ids.filtered(lambda x: x.reconcile)
    #                 liquidity_amount += sum(mv_ids.mapped('it_wht_amt')) + sum(mv_ids.mapped('st_wht_amt'))

    #             # Overwrite amount_currency and balance for liquidity line
    #             currency = pay.currency_id
    #             company_currency = pay.company_id.currency_id
    #             converted_amount = currency._convert(
    #                 liquidity_amount,
    #                 company_currency,
    #                 pay.company_id,
    #                 fields.Date.context_today(pay),
    #             )

    #             line_vals_list[0]['amount_currency'] = liquidity_amount * (1 if pay.payment_type == 'inbound' else -1)
    #             line_vals_list[0]['balance'] = converted_amount * (1 if pay.payment_type == 'inbound' else -1)

    #         # =====================================
    #         # Ensure that line_vals_list is balanced
    #         # =====================================
    #         total_balance = sum(line['balance'] for line in line_vals_list)
    #         if round(total_balance, 2) != 0.0:
    #             raise UserError("Unbalanced journal entry. Please check the WHT and payment values.")

    #         # ====================
    #         # Build line commands
    #         # ====================
    #         line_ids_commands = [
    #             Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
    #             Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
    #         ]

    #         for line in writeoff_lines:
    #             line_ids_commands.append((2, line.id))
    #         for extra_line_vals in line_vals_list[2:]:
    #             line_ids_commands.append((0, 0, extra_line_vals))

    #         # ===========================
    #         # Write changes to account.move
    #         # ===========================
    #         pay.move_id.with_context(skip_invoice_sync=True).write({
    #             'partner_id': pay.partner_id.id,
    #             'currency_id': pay.currency_id.id,
    #             'partner_bank_id': pay.partner_bank_id.id,
    #             'line_ids': line_ids_commands,
    #         })


    # def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
    #     res = super(AccountPayment, self)._generate_journal_entry(write_off_line_vals=write_off_line_vals, force_balance=force_balance, line_ids=line_ids)
    #     raise UserError(str(self.read()))

        # need_move = self.filtered(lambda p: not p.move_id and p.outstanding_account_id)
        # assert len(self) == 1 or (not write_off_line_vals and not force_balance and not line_ids)

        # move_vals = []
        # for pay in need_move:
        #     move_vals.append({
        #         'move_type': 'entry',
        #         'ref': pay.memo,
        #         'date': pay.date,
        #         'journal_id': pay.journal_id.id,
        #         'company_id': pay.company_id.id,
        #         'partner_id': pay.partner_id.id,
        #         'currency_id': pay.currency_id.id,
        #         'partner_bank_id': pay.partner_bank_id.id,
        #         'line_ids': line_ids or [
        #             Command.create(line_vals)
        #             for line_vals in pay._prepare_move_line_default_vals(
        #                 write_off_line_vals=write_off_line_vals,
        #                 force_balance=force_balance,
        #             )
        #         ],
        #         'origin_payment_id': pay.id,
        #     })
        # moves = self.env['account.move'].create(move_vals)
        # for pay, move in zip(need_move, moves):
        #     pay.write({'move_id': move.id, 'state': 'in_process'})

    # 18890 / 52400 Muhammad Ashhad Jamal
    gst_tax_id = fields.Many2one(
        'account.tax',
        string='GST Withhold Percentage',
        domain=[('tds', '=', True), ('wht_type', '=', 'income_tax')],
        context={},
    )
    gst_withholding_type = fields.Selection(
        string='GST Withhold Type',
        selection=[
            ('default', 'Payment Without GST'),
            ('including', 'Payment Including GST'),
        ],
        required=True,
        context={},
        default="default",
    )

    td_amt = fields.Monetary(
        string='GST Withhold Amount',
        compute='_compute_withholding_amounts',
        context={},
    )

    @api.depends('gst_withholding_type', 'gst_tax_id', 'amount')
    def _compute_withholding_amounts(self):
        for payment in self:
            payment.td_amt = 0.0
    
            # Only compute when GST is applicable
            if (
                payment.gst_withholding_type == 'including'
                and payment.gst_tax_id
                and payment.amount
            ):
                gst_tax = payment.gst_tax_id
    
            
                if not payment.reconcile_invoice_ids or not payment.reconcile_invoice_ids.filtered('reconcile'):
                    payment.td_amt = payment.amount * gst_tax.amount / 100

                else:
                    gst_amounts = []
                    for line in payment.reconcile_invoice_ids.filtered('reconcile'):
                        base_amount = (
                            line.amount_total
                            if line.full_wht_deduction
                            else line.amount_paid
                        )
                        gst_amounts.append(base_amount * gst_tax.amount / 100)
    
                    payment.td_amt = sum(gst_amounts)
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        for payment in self:
            if payment.payment_type == 'inbound':  # Customer payment
                return {'domain': {'gst_tax_id': [('type_tax_use', '=', 'sale')]}}
            elif payment.payment_type == 'outbound':  # Vendor payment
                return {'domain': {'gst_tax_id': [('type_tax_use', '=', 'purchase')]}}

    # 18890 / 52400 Muhammad Ashhad Jamal


class AccountPaymentReconcile(models.Model):
    _name = 'account.payment.reconcile'

    def _check_full_deduction(self):
        if self.invoice_id:
            payment_ids = [payment['account_payment_id'] for payment in
                           self.invoice_id._get_reconciled_invoices_partials()]
            if payment_ids:
                payments = self.env['account.payment'].browse(payment_ids)
                return any([True if payment.tds_amt or payment.sales_tds_amt else False for payment in payments])
            else:
                return False

    payment_id = fields.Many2one('account.payment')
    reconcile = fields.Boolean(string="Select")
    invoice_id = fields.Many2one('account.move', required=True)
    currency_id = fields.Many2one('res.currency')
    amount_total = fields.Monetary(string='Total')
    amount_untaxed = fields.Monetary(string='Untaxed Amount')
    amount_tax = fields.Monetary(string='Taxes Amount')
    already_paid = fields.Float("Amount Paid")
    amount_residual = fields.Monetary('Amount Due')
    full_wht_deduction = fields.Boolean('Full DED. WHT')
    is_editable_deduction = fields.Boolean(default=lambda self: self._check_full_deduction())
    amount_paid = fields.Monetary(string="Payment Amount")
    it_wht_amount = fields.Monetary(string="IT WHT Amount", compute='_compute_wht_amount', inverse='_inverse_it_wht_amount', store=True)
    st_wht_amount = fields.Monetary(string="ST WHT Amount", compute='_compute_wht_amount', inverse='_inverse_st_wht_amount', store=True)
    # 18890 / 52400 Muhammad Ashhad Jamal
    gst_wht_amount = fields.Monetary(
        string="GST WHT Amount",
        compute='_compute_wht_amount',
        inverse='_inverse_gst_wht_amount',
        store=True
    )
    # 18890 / 52400 Muhammad Ashhad Jamal
    it_wht_amt = fields.Monetary(string="IT WHT Amount")
    st_wht_amt = fields.Monetary(string="ST WHT Amount")

    def _inverse_it_wht_amount(self):
        pass

    def _inverse_st_wht_amount(self):
        pass

    # 18890 / 52400 Muhammad Ashhad Jamal
    def _inverse_gst_wht_amount(self):
        pass
    # 18890 / 52400 Muhammad Ashhad Jamal
    @api.constrains('it_wht_amount', 'st_wht_amount')
    def _check_amount_paid(self):
        for line in self.filtered(lambda x: x.reconcile):
            if line.it_wht_amt > line.amount_residual:
                raise UserError('WHT amount should be less than or equal to amount due')
            if line.st_wht_amt > line.amount_tax:
                raise UserError('WHT amount should be less than or equal to taxes amount')

    # 18890 / 52400 Muhammad Ashhad Jamal
    @api.depends('amount_paid', 'payment_id.tds_tax_id', 'payment_id.sales_tds_tax_id', 'full_wht_deduction', 'payment_id.gst_tax_id')
    def _compute_wht_amount(self):
        for line in self:
            if line.amount_paid > line.amount_residual:
                raise ValidationError(_('You cannot paid more than due amount.'))
            
            wht_id = line.payment_id.sales_tds_tax_id
            income_tax_id = line.payment_id.tds_tax_id
            gst_tax_id = line.payment_id.gst_tax_id  # Get GST tax
            
            if line.full_wht_deduction:
                # Full deduction calculation
                line.it_wht_amount = line.amount_total * income_tax_id.amount / 100 if income_tax_id else 0.0
                line.st_wht_amount = line.amount_tax * wht_id.amount / 100 if wht_id else 0.0
                
                # GST calculation based on full amount
                if gst_tax_id and line.payment_id.gst_withholding_type == 'including':
                    line.gst_wht_amount = line.amount_total * gst_tax_id.amount / 100
                else:
                    line.gst_wht_amount = 0.0
            else:
                # Partial payment calculation
                line.it_wht_amount = line.amount_paid * income_tax_id.amount / 100 if income_tax_id else 0.0
                
                payment_per = line.amount_paid / line.amount_total * 100 if line.amount_total else 0.0
                tot_sales_tax = line.amount_tax * wht_id.amount / 100 if wht_id else 0.0
                line.st_wht_amount = tot_sales_tax * payment_per / 100
                
                # GST calculation based on partial payment
                if gst_tax_id and line.payment_id.gst_withholding_type == 'including':
                    line.gst_wht_amount = line.amount_paid * gst_tax_id.amount / 100
                else:
                    line.gst_wht_amount = 0.0
    # 18890 / 52400 Muhammad Ashhad Jamal


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    wht_type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], default='amount')
    sales_tds_type = fields.Selection([('default', 'Payment Without WHT'), ('including', 'Payment Including WHT'),
                                       ('excluding', 'Payment Excluding With WHT')], default="default",
                                      string="Sales Tax Withhold Type")
    sales_tds_tax_id = fields.Many2one('account.tax', string='Sales Tax Withhold Percentage')
    sales_tds_amt = fields.Monetary(string='Sales Tax Withhold Amount', compute='compute_sales_tds_amnt')
    tds_type = fields.Selection([('default', 'Payment Without WHT'), ('including', 'Payment Including WHT'),
                                 ('excluding', 'Payment Excluding With WHT')], default="default",
                                string="Income Tax Withhold Type")
    tds_tax_id = fields.Many2one('account.tax', string='Incomte Tax Withhold Percentage')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.company.currency_id)
    tds_amt = fields.Monetary(string='Income Tax Withhold Amount', compute='compute_tds_amnt')
    reconcile_invoice_ids = fields.Many2many('account.payment.reconcile', string="Invoices", copy=False)
    income_account_id = fields.Many2one('account.account', 'GL Income Tax WHT')
    sales_account_id = fields.Many2one('account.account', 'GL Sales Tax WHT')

    @api.depends('sales_tds_type', 'sales_tds_tax_id', 'amount')
    def compute_sales_tds_amnt(self):
        for payment in self:
            wht_id = payment.sales_tds_tax_id
            payment.sales_tds_amt = 0.0
            if payment.sales_tds_type in ('including', 'excluding') and payment.sales_tds_tax_id and payment.amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = True
                if applicable and payment.sales_tds_type in ['excluding', 'including'] and payment.amount:
                    if not payment.reconcile_invoice_ids or len(
                            payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile)) == 0:
                        amount = payment.sales_tds_tax_id.amount
                        payment.sales_tds_amt = (payment.amount * amount / 100)
                    else:
                        for line in payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile):
                            if line.full_wht_deduction:
                                line.st_wht_amount = line.amount_tax * wht_id.amount / 100
                            else:
                                payment_per = line.amount_paid / line.amount_total * 100 if line.amount_total else 0.0
                                tot_sales_tax = line.amount_tax * wht_id.amount / 100
                                line.st_wht_amount = tot_sales_tax * payment_per / 100
                        payment.sales_tds_amt = sum(
                            payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('st_wht_amount'))

    @api.onchange('reconcile_invoice_ids')
    def _onchnage_reconcile_invoice_ids(self):
        self.amount = sum(self.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('amount_paid'))

    @api.depends('tds_type', 'tds_tax_id', 'amount')
    def compute_tds_amnt(self):
        for payment in self:
            income_tax_id = payment.tds_tax_id
            payment.tds_amt = 0.0
            if payment.tds_type in ('including', 'excluding') and payment.tds_tax_id and payment.amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = True
                if applicable and payment.tds_type == 'including':

                    if not payment.reconcile_invoice_ids or len(
                            payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile)) == 0:
                        tds_amount = payment.tds_tax_id.amount
                        payment.tds_amt = (payment.amount * tds_amount / 100)
                    else:
                        for line in payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile):
                            if line.full_wht_deduction:
                                line.it_wht_amount = line.amount_total * income_tax_id.amount / 100
                            else:
                                line.it_wht_amount = line.amount_paid * income_tax_id.amount / 100
                        payment.tds_amt = sum(
                            payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('it_wht_amount'))

    # @api.model
    # def default_get(self, fields):
    #     res = super(AccountPaymentRegister, self).default_get(fields)
    #     moves = self.env['account.move'].browse(self._context.get('active_ids', []))
    #     res.update({'reconcile_invoice_ids': [(0, 0, {'invoice_id': move.id, 'already_paid': sum(
    #         [payment['amount'] for payment in move._get_reconciled_invoices_partials()]),
    #                                                   'amount_residual': move.amount_residual,
    #                                                   'amount_untaxed': move.amount_untaxed,
    #                                                   'amount_tax': move.amount_tax, 'currency_id': move.currency_id.id,
    #                                                   'amount_total': move.amount_total, }) for move in moves],
    #                 'sales_tds_tax_id': moves.partner_id.wht_id.id, 'tds_tax_id': moves.partner_id.income_tax_id.id})
    #     return res

    def _create_payment_vals_from_wizard(self,batch_result):
        # OVERRIDE
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)
        moves = self.env['account.move'].browse(self._context.get('active_ids', []))
        reconcile_lines = []
        for line in self.reconcile_invoice_ids:
            reconcile_lines.append((0, 0, {
                'reconcile': line.reconcile,
                'invoice_id': line.invoice_id.id,
                'currency_id': line.currency_id.id,
                'amount_total': line.amount_total,
                'amount_untaxed': line.amount_untaxed,
                'amount_tax': line.amount_tax,
                'already_paid': line.already_paid,
                'amount_residual': line.amount_residual,
                'full_wht_deduction': line.full_wht_deduction,
                'is_editable_deduction': line.is_editable_deduction,
                'amount_paid': line.amount_paid,
                'it_wht_amount': line.it_wht_amount,
                'st_wht_amount': line.st_wht_amount,
                'it_wht_amt': line.it_wht_amt,
                'st_wht_amt': line.st_wht_amt,
        }))
        payment_vals.update({
            'wht_type': self.wht_type,
            'income_account_id': self.income_account_id.id,
            'sales_account_id': self.sales_account_id.id,
            'sales_tds_type': self.sales_tds_type,
            'sales_tds_tax_id': self.sales_tds_tax_id.id,
            'tds_type': self.tds_type,
            'tds_tax_id': self.tds_tax_id.id,
            'reconcile_invoice_ids': reconcile_lines,
        })
        return payment_vals
