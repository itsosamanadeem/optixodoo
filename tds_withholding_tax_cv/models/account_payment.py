# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError


class account_payment(models.Model):
    _inherit = "account.payment"

    # tds = fields.Boolean('Apply WHT', default=False)
    tds_type = fields.Selection([('default', 'Payment Without WHT'), ('including', 'Payment Including WHT'),
                                 ], default="default",
                                string="Income Tax Withhold Type")
    
    # ('excluding', 'Payment Excluding With WHT')
    wht_type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], default='percentage')
    tds_tax_id = fields.Many2one('account.tax', string='Incomte Tax Withhold Percentage')
    tds_amt = fields.Monetary(string='Income Tax Withhold Amount', compute='compute_tds_amnt')
    vendor_type = fields.Selection(related='partner_id.company_type', string='Partner Type')

    bill_type = fields.Selection([('bill', 'Bill'), ('non_bill', 'Non Bill')], default="bill", string="Bill Type")
    sales_tds_type = fields.Selection([('default', 'Payment Without WHT'), ('including', 'Payment Including WHT'),
                                       ], default="default",
                                      string="Sales Tax Withhold Type")
    # ('excluding', 'Payment Excluding With WHT')
    sales_tds_tax_id = fields.Many2one('account.tax', string='Sales Tax Withhold Percentage')
    sales_tds_amt = fields.Monetary(string='Sales Tax Withhold Amount', compute='compute_sales_tds_amnt')
    income_account_id = fields.Many2one('account.account', 'GL Income Tax WHT')
    sales_account_id = fields.Many2one('account.account', 'GL Sales Tax WHT')
    gst_account_id = fields.Many2one('account.account', 'GL GST WHT')

    def _get_reconcile_invoice_lines(self):
        """Return reconcile lines when available (older custom flow), else empty."""
        self.ensure_one()
        if 'reconcile_invoice_ids' in self._fields:
            return self.reconcile_invoice_ids
        return self.env['account.move'].browse()

    def _get_selected_reconcile_invoice_lines(self):
        self.ensure_one()
        return self._get_reconcile_invoice_lines().filtered(lambda x: getattr(x, 'reconcile', False))

    def _sum_reconcile_field(self, lines, field_name):
        if not lines or field_name not in lines._fields:
            return 0.0
        return sum(lines.mapped(field_name))

    def _any_reconcile_field_positive(self, lines, field_name):
        if not lines or field_name not in lines._fields:
            return False
        return any((value or 0.0) > 0 for value in lines.mapped(field_name))

    @api.constrains('reconcile_invoice_ids', 'td_amt')
    def _check_gl_accounts(self):
        for payment in self:
            reconcile_lines = payment._get_selected_reconcile_invoice_lines()
            if payment._any_reconcile_field_positive(reconcile_lines, 'st_wht_amt') and not payment.sales_account_id:
                raise ValidationError(_('Please select GL Sales Tax WHT on payment.'))
            if payment._any_reconcile_field_positive(reconcile_lines, 'it_wht_amt') and not payment.income_account_id:
                raise ValidationError(_('Please select GL Income Tax WHT on payment.'))

    # def write(self, vals):
    #     if 'reconcile_invoice_ids' in vals:
    #         raise ValidationError(_('You cannot update reconcile amount, please cancel the payment and create again.'))
    #     return super(account_payment, self).write(vals)

    # @api.onchange('wht_type')
    # def _onchange_wht_type(self):
    #     if self.wht_type:
    #         self.sales_tds_type = 'default'
    #         self.tds_type = 'default'

    @api.onchange('partner_id')
    def GetTaxDetailOfPartner(self):
        if self.partner_type == 'supplier':
            if self.partner_id and self.partner_id.income_tax_id:
                if self.partner_id.income_wht:
                    self.tds_type = 'including'
                    self.tds_tax_id = self.partner_id.income_tax_id.id
            if self.partner_id and self.partner_id.tds_threshold_check:
                if self.partner_id.tds_threshold_check:
                    self.sales_tds_type = 'including'
                    self.tds_tax_id = self.partner_id.wht_id.id

    @api.onchange('tds_type', 'partner_id')
    def set_default_tds_tax_id(self):
        if self.partner_id.income_tax_id and self.tds_type == 'including':
            self.tds_tax_id = self.partner_id.income_tax_id.id
        else:
            self.tds_tax_id = False

    @api.onchange('sales_tds_type', 'partner_id')
    def set_default_sales_tds_tax_id(self):
        if self.partner_id.wht_id and self.sales_tds_type == 'including':
            self.sales_tds_tax_id = self.partner_id.wht_id.id
        else:
            self.sales_tds_tax_id = False

    @api.depends('sales_tds_type', 'sales_tds_tax_id', 'amount')
    def compute_sales_tds_amnt(self):
        for payment in self:
            payment.sales_tds_amt = 0.0
            if payment.sales_tds_type in ('including', 'excluding') and payment.sales_tds_tax_id and payment.amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = payment.check_turnover(payment.partner_id.id, payment.sales_tds_tax_id.payment_excess,
                                                        payment.amount)
                if applicable and payment.sales_tds_type in ['excluding',
                                                             'including'] and payment.amount and payment.bill_type == 'non_bill':
                    amount = payment.sales_tds_tax_id.amount
                    payment.sales_tds_amt = (payment.amount * amount / 100)
                if applicable and payment.sales_tds_type in ['excluding',
                                                             'including'] and payment.amount and payment.bill_type == 'bill':
                    reconcile_lines = payment._get_selected_reconcile_invoice_lines()
                    if not reconcile_lines:
                        amount = payment.sales_tds_tax_id.amount
                        payment.sales_tds_amt = (payment.amount * amount / 100)
                    else:
                        if payment.wht_type == 'percentage':
                            payment.sales_tds_amt = payment._sum_reconcile_field(reconcile_lines, 'st_wht_amount')
                        else:
                            payment.sales_tds_amt = payment._sum_reconcile_field(reconcile_lines, 'st_wht_amt')

            else:
                reconcile_lines = payment._get_selected_reconcile_invoice_lines()
                if payment.wht_type == 'percentage':
                    payment.sales_tds_amt = payment._sum_reconcile_field(reconcile_lines, 'st_wht_amount')
                else:
                    payment.sales_tds_amt = payment._sum_reconcile_field(reconcile_lines, 'st_wht_amt')

    @api.depends('tds_type', 'tds_tax_id', 'amount')
    def compute_tds_amnt(self):
        for payment in self:
            payment.tds_amt = 0.0
            if payment.tds_type in ('including', 'excluding') and payment.tds_tax_id and payment.amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = payment.check_turnover(payment.partner_id.id, payment.tds_tax_id.payment_excess, payment.amount)
                if applicable and payment.tds_type == 'including':
                    reconcile_lines = payment._get_selected_reconcile_invoice_lines()
                    if not reconcile_lines:
                        tds_amount = payment.tds_tax_id.amount
                        payment.tds_amt = (payment.amount * tds_amount / 100)
                    else:
                        if payment.wht_type == 'percentage':
                            payment.tds_amt = payment._sum_reconcile_field(reconcile_lines, 'it_wht_amount')
                        else:
                            payment.tds_amt = payment._sum_reconcile_field(reconcile_lines, 'it_wht_amt')

            else:
                reconcile_lines = payment._get_selected_reconcile_invoice_lines()
                if payment.wht_type == 'percentage':
                    payment.tds_amt = payment._sum_reconcile_field(reconcile_lines, 'it_wht_amount')
                else:
                    payment.tds_amt = payment._sum_reconcile_field(reconcile_lines, 'it_wht_amt')

    def check_turnover(self, partner_id, threshold, amount):
        if self.payment_type == 'outbound':
            domain = [('partner_id', '=', partner_id), ('account_id.account_type', '=', 'payable'),
                      ('move_id.state', '=', 'posted'), ('account_id.reconcile', '=', True)]
            journal_items = self.env['account.move.line'].search(domain)
            credits = sum([item.credit for item in journal_items])
            credits += amount
            if credits >= threshold:
                return True
            else:
                return False
        elif self.payment_type == 'inbound':
            domain = [('partner_id', '=', partner_id), ('account_id.account_type', '=', 'receivable'),
                      ('move_id.state', '=', 'posted'), ('account_id.reconcile', '=', True)]
            journal_items = self.env['account.move.line'].search(domain)
            debits = sum([item.debit for item in journal_items])
            debits += amount
            if debits >= threshold:
                return True
            else:
                return False

    # def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
    #     all_move_vals = super(account_payment, self)._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance)
        
    #     new_vals = []
    #     for line in all_move_vals:
    #         if not line.get('for_wht') or 'Withhold' in line.get('name'):
    #             new_vals.append(line)
    #     all_move_vals = new_vals
    #     # write_off_line_vals_list = write_off_line_vals or []
    #     # write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
    #     # write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)
    #     for payment in self:
    #         if payment.currency_id == payment.company_id.currency_id:
    #             currency_id = payment.currency_id.id
    #         else:
    #             currency_id = payment.currency_id.id
    #         tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
    #             lambda x: x.repartition_type == 'tax')
    #         sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
    #             lambda x: x.repartition_type == 'tax')
    #         # raise UserError(currency_id)
    #         income_tax_vals = {
    #             'name': _('Income Tax Withhold'),
    #             'currency_id': currency_id,
    #             'for_wht': True,
    #             'date_maturity': payment.create_date,
    #             'partner_id': payment.partner_id.id,
    #             'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id or payment.income_account_id.id,
    #             'payment_id': payment.id,
    #         }

    #         sales_tax_vals = {
    #             'name': _('Salse Tax Withhold'),
    #             'currency_id': currency_id,
    #             'for_wht': True,
    #             'date_maturity': payment.create_date,
    #             'partner_id': payment.partner_id.id,
    #             'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id or payment.sales_account_id.id,
    #             'payment_id': payment.id,
    #         }
    #         # raise 
    #         if payment.payment_type == 'outbound':
    #             debit = 0
    #             total_credit = 0
    #             if payment.tds_amt and (payment.tds_type == 'including' or payment.income_account_id):
    #                 credit = payment.tds_amt
    #                 income_tax_vals.update({'credit': credit, 'debit': debit})
    #                 all_move_vals.append(income_tax_vals)
    #                 total_credit += credit
    #                 # raise UserError(str(all_move_vals))

    #             if payment.sales_tds_amt and (payment.sales_tds_type == 'including' or payment.sales_account_id):
    #                 credit = payment.sales_tds_amt
    #                 sales_tax_vals.update({'credit': credit, 'debit': debit})
    #                 all_move_vals.append(sales_tax_vals)
    #                 total_credit += credit

    #             # Reduce from original credit line
    #             # if total_credit and all_move_vals:
    #             #     all_move_vals[0]['credit'] = all_move_vals[0].get('credit', 0) - total_credit
    #             # debit = 0


    #         if payment.payment_type == 'inbound':
    #             credit = 0
    #             total_debit = 0
    #             if payment.tds_amt and (payment.tds_type == 'including' or payment.income_account_id):
    #                 debit = payment.tds_amt
    #                 income_tax_vals.update({'credit': credit, 'debit': debit})
    #                 all_move_vals.append(income_tax_vals)
    #                 total_debit += debit

    #             if payment.sales_tds_amt and (payment.sales_tds_type == 'including' or payment.sales_account_id):
    #                 debit = payment.sales_tds_amt
    #                 sales_tax_vals.update({'credit': credit, 'debit': debit})
    #                 all_move_vals.append(sales_tax_vals)
    #                 total_debit += debit

    #             # Reduce from original debit line
    #             # if total_debit and all_move_vals:
    #             #     all_move_vals[0]['debit'] = all_move_vals[0].get('debit', 0) - total_debit

                
            
    #     return all_move_vals 
    # def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
    #     all_move_vals = super(account_payment, self)._prepare_move_line_default_vals(
    #         write_off_line_vals=write_off_line_vals,
    #         force_balance=force_balance
    #     )

    #     # Remove existing WHT lines (for_wht or containing 'Withhold')
    #     all_move_vals = [
    #         line for line in all_move_vals
    #         if not line.get('for_wht') and 'Withhold' not in line.get('name', '')
    #     ]

    #     for payment in self:
    #         currency_id = payment.currency_id.id
    #         tax_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax')
    #         sales_tax_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax')

    #         def build_tax_line(name, account, amount, is_credit):
    #             return {
    #                 'name': name,
    #                 'currency_id': currency_id,
    #                 'for_wht': True,
    #                 'date_maturity': payment.date,
    #                 'partner_id': payment.partner_id.id,
    #                 'account_id': account.id if account else False,
    #                 'payment_id': payment.id,
    #                 'credit': amount if is_credit else 0.0,
    #                 'debit': 0.0 if is_credit else amount,
    #             }

    #         total_offset = 0.0
    #         is_outbound = payment.payment_type == 'outbound'
    #         is_inbound = payment.payment_type == 'inbound'

    #         # Income Tax (WHT)
    #         if payment.tds_amt and (payment.tds_type == 'including' or payment.income_account_id):
    #             account = tax_lines.account_id or payment.income_account_id
    #             move_line = build_tax_line(_('Income Tax Withhold'), account, payment.tds_amt, is_credit=is_outbound)
    #             total_offset += payment.tds_amt
    #             all_move_vals.append(move_line)

    #         # Sales Tax (WHT)
    #         if payment.sales_tds_amt and (payment.sales_tds_type == 'including' or payment.sales_account_id):
    #             account = sales_tax_lines.account_id or payment.sales_account_id
    #             move_line = build_tax_line(_('Sales Tax Withhold'), account, payment.sales_tds_amt, is_credit=is_outbound)
    #             total_offset += payment.sales_tds_amt
    #             all_move_vals.append(move_line)

    #         # Adjust original line (assumed at index 0: liquidity line)
    #         if all_move_vals and total_offset:
    #             if is_outbound:
    #                 all_move_vals[0]['credit'] = all_move_vals[0].get('credit', 0.0) - total_offset
    #             elif is_inbound:
    #                 all_move_vals[0]['debit'] = all_move_vals[0].get('debit', 0.0) - total_offset

    #     return all_move_vals


    # def _create_payment_entry(self, amount):
    #     applicable = True
    #     if self.partner_id and self.partner_id.tds_threshold_check:
    #         applicable = self.check_turnover(self.partner_id.id, self.tds_tax_id.payment_excess, amount)
    #     if self.tds_type in ('including', 'excluding') and self.tds_tax_id and self.tds_amt and applicable:
    #         aml_obj = self.env['account.move.line'].with_context(_check_balanced=False)
    #         invoice_currency = False
    #         if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
    #             # if all the invoices selected share the same currency, record the payment in that currency too
    #             invoice_currency = self.invoice_ids[0].currency_id
    #         debit, credit, amount_currency, currency_id = aml_obj.with_context(
    #             date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
    #         move = self.env['account.move'].with_context(_check_balanced=False).create(self._get_move_vals())

    #         # Write line corresponding to invoice payment
    #         counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
    #         counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
    #         counterpart_aml_dict.update({'currency_id': currency_id})
    #         counterpart_aml = aml_obj.with_context(_check_balanced=False).create(counterpart_aml_dict)

    #         # Reconcile with the invoices
    #         payment_difference_handling = 'reconcile'
    #         payment_difference = self.tds_amt
    #         writeoff_account_id = self.tds_tax_id and self.tds_tax_id.account_id

    #         if payment_difference_handling == 'reconcile' and payment_difference:
    #             writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
    #             debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(
    #                 date=self.payment_date)._compute_amount_fields(payment_difference, self.currency_id,
    #                                                                self.company_id.currency_id)
    #             writeoff_line['name'] = _('Counterpart')
    #             writeoff_line['account_id'] = writeoff_account_id.id
    #             writeoff_line['debit'] = debit_wo
    #             writeoff_line['credit'] = credit_wo
    #             writeoff_line['amount_currency'] = amount_currency_wo
    #             writeoff_line['currency_id'] = currency_id
    #             writeoff_line = aml_obj.with_context(_check_balanced=False).create(writeoff_line)
    #             if counterpart_aml['debit']:
    #                 counterpart_aml['debit'] += credit_wo - debit_wo
    #             if counterpart_aml['credit']:
    #                 counterpart_aml['credit'] += debit_wo - credit_wo
    #             counterpart_aml['amount_currency'] -= amount_currency_wo
    #         # raise UserError(counterpart_aml)
    #         self.invoice_ids.register_payment(counterpart_aml)

    #         # Write counterpart lines
    #         if not self.currency_id != self.company_id.currency_id:
    #             amount_currency = 0
    #         liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
    #         liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
    #         aml_obj.with_context(_check_balanced=False).create(liquidity_aml_dict)

    #         move.post()
    #         return move
    #     return super(account_payment, self)._create_payment_entry(amount)



    def write(self,vals):
        res = super(account_payment, self).write(vals)
        if 'state' in vals:
            self._onchange_state()
        # self._onchange_state(vals)
        return res
    # @api.constrains('state')
    def _onchange_state(self):
        for rec in self:
            if rec.state in ['in_process','paid'] and rec.move_id and rec.move_id.line_ids or rec.sales_tds_amt or rec.tds_amt:
                # raise UserError(rec.state)
                ##Vendor Payment
                if rec.payment_type == 'inbound':
                    # if 'amount' in vals and 'deduction_ids' in vals:
                        move = rec.move_id
                        if move.state == 'posted':
                            move.button_draft()
                        label = 'Manual'
                        # Reset the move lines
                        move.line_ids.unlink()

                        # Prepare the list of line updates
                        line_updates = []

                        # Debit line for the actual amount
                        line_updates.append((0, 0, {
                            'move_id': move.id,
                            'name': label or '',
                            'account_id': rec.outstanding_account_id.id,
                            'debit': rec.actual_amount,
                            'credit': 0.0,
                            'partner_id':rec.partner_id.id
                            # 'sequence':20,
                        }))

                        # Credit lines for each deduction
                        line_updates.append((0, 0, {
                            'move_id': move.id,
                            'name': label or '',
                            'account_id': rec.destination_account_id.id,
                            'debit': 0.0,
                            'credit': rec.amount,
                            'partner_id':rec.partner_id.id
                        }))
                        
                        if rec.sales_tds_amt:
                            line_updates.append((0, 0, {
                                'move_id': move.id,
                                # 'name': 'Salse Tax Withhold',
                                'name': rec.sales_tds_tax_id.name if rec.sales_tds_tax_id else '',
                                'account_id': rec.sales_tds_tax_id.invoice_repartition_line_ids[1].account_id.id if rec.sales_tds_tax_id.invoice_repartition_line_ids else 6174,
                                'debit': rec.sales_tds_amt,
                                'credit': 0.0,
                                'partner_id':rec.partner_id.id
                            }))

                        if rec.tds_amt:
                            line_updates.append((0, 0, {
                                'move_id': move.id,
                                # 'name': 'Income Tax Withhold',
                                'name': rec.tds_tax_id.name if rec.tds_tax_id else '',
                                'account_id': rec.tds_tax_id.invoice_repartition_line_ids[1].account_id.id if rec.tds_tax_id.invoice_repartition_line_ids else 6152,
                                'debit': rec.tds_amt,
                                'credit': 0.0,
                                'partner_id':rec.partner_id.id
                            }))

                        
                        # GST Withholding Tax
                        if rec.td_amt:
    # Try to get account from tax configuration
                            gst_account = False
                            if rec.gst_account_id:
                                gst_account = rec.gst_account_id.id
                            elif rec.gst_tax_id and rec.gst_tax_id.invoice_repartition_line_ids:
                                # Find the tax line (not base line)
                                tax_lines = rec.gst_tax_id.invoice_repartition_line_ids.filtered(
                                    lambda l: l.repartition_type == 'tax'
                                )
                                if tax_lines and tax_lines[0].account_id:
                                    gst_account = tax_lines[0].account_id.id
                            
                            if not gst_account:
                                raise ValidationError(
                                    _('GST Withholding account not configured. '
                                    'Please set GL GST WHT or configure the account in tax settings.')
                                )
                            
                            line_updates.append((0, 0, {
                                'move_id': move.id,
                                'name': rec.gst_tax_id.name if rec.gst_tax_id else 'GST Withhold',
                                'account_id': gst_account,
                                'credit' if rec.payment_type == 'outbound' else 'debit': rec.td_amt,
                                'debit' if rec.payment_type == 'outbound' else 'credit': 0.0,
                                'partner_id': rec.partner_id.id
                            }))

                        move.write({'line_ids': line_updates})
                        move.action_post()

                ##Customer Payment
                elif rec.payment_type == 'outbound':
                    # if 'amount' in vals and 'deduction_ids' in vals:
                        move = rec.move_id
                        if move.state == 'posted':
                            move.button_draft()
                        # label = move.line_ids[0].name
                        label = 'Manual'
                        # Reset the move lines
                        move.line_ids.unlink()

                        # Prepare the list of line updates
                        line_updates = []

                        # Debit line for the actual amount
                        line_updates.append((0, 0, {
                            'move_id': move.id,
                            'name': label or '',
                            'account_id': rec.outstanding_account_id.id,
                            'credit': rec.actual_amount,
                            'debit': 0.0,
                            'partner_id':rec.partner_id.id
                        }))

                        # Credit lines for each deduction
                        line_updates.append((0, 0, {
                            'move_id': move.id,
                            'name': label or '',
                            'account_id': rec.destination_account_id.id,
                            'credit': 0.0,
                            'debit': rec.amount,
                            'partner_id':rec.partner_id.id
                        }))
                        
                        if rec.sales_tds_amt:
                            line_updates.append((0, 0, {
                                'move_id': move.id,
                                # 'name': 'Salse Tax Withhold',
                                'name': rec.sales_tds_tax_id.name if rec.sales_tds_tax_id else '',
                                'account_id': rec.sales_tds_tax_id.invoice_repartition_line_ids[1].account_id.id if rec.sales_tds_tax_id.invoice_repartition_line_ids else 6174,
                                'credit': rec.sales_tds_amt,
                                'debit': 0.0,
                                'partner_id':rec.partner_id.id
                            }))

                        if rec.tds_amt:
                            line_updates.append((0, 0, {
                                'move_id': move.id,
                                # 'name': 'Income Tax Withhold',
                                'name': rec.tds_tax_id.name if rec.tds_tax_id else '',
                                'account_id': rec.tds_tax_id.invoice_repartition_line_ids[1].account_id.id if rec.tds_tax_id.invoice_repartition_line_ids else 6152,
                                'credit': rec.tds_amt,
                                'debit': 0.0,
                                'partner_id':rec.partner_id.id
                            }))

                        
                        # GST Withholding Tax
                        if rec.td_amt:
                            gst_account = rec.gst_account_id.id if rec.gst_account_id else (
                                rec.gst_tax_id.invoice_repartition_line_ids[1].account_id.id 
                                if rec.gst_tax_id and rec.gst_tax_id.invoice_repartition_line_ids 
                                else False
                            )
                            line_updates.append((0, 0, {
                                'move_id': move.id,
                                'name': rec.gst_tax_id.name if rec.gst_tax_id else 'GST Withhold',
                                'account_id': gst_account,
                                'credit': rec.td_amt,
                                'debit': 0.0,
                                'partner_id':rec.partner_id.id
                            }))

                        move.write({'line_ids': line_updates})
                        move.action_post()

                # credit_line = rec.move_id.line_ids.filtered(lambda l: l.credit and l.account_id == self.company_data['default_account_receivable'])


            
            # elif rec.state == 'paid' :
            for invoice in rec._get_reconcile_invoice_lines():
                if invoice.reconcile and invoice.amount_paid == invoice.amount_residual:
                    move_lines = rec.move_id.line_ids.filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable') and not line.reconciled)
                    for line in move_lines:
                        invoice.invoice_id.js_assign_outstanding_line(line.id)
                elif invoice.reconcile and invoice.amount_paid <= invoice.amount_residual:
                    payment_line = rec.move_id.line_ids.filtered(
                        lambda l: l.account_type in ('asset_receivable', 'liability_payable') 
                    )
                    invoice_line = invoice.invoice_id.line_ids.filtered(
                        lambda l: l.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                    )
                    if len(invoice_line) > 1:
                        invoice_line = invoice_line[:1]
                    if payment_line and invoice_line:
                        self.env['account.partial.reconcile'].create({
                            'debit_move_id': invoice_line.id if invoice_line.debit > 0 else payment_line.id,
                            'credit_move_id': payment_line.id if invoice_line.debit > 0 else invoice_line.id,
                            'amount': invoice.amount_paid,
                            'debit_amount_currency': invoice.amount_paid,
                            'credit_amount_currency': invoice.amount_paid,
                        })
                            # raise UserError(str(invoice.read()))
