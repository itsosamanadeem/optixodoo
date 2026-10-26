from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError


class PaymentTaxMixin(models.AbstractModel):
    _name = 'optix.payment.tax.mixin'
    _description = 'Payment deduction calculation'

    tax_id = fields.Many2one('account.tax', required=True, check_company=True,
        domain="[('payment_tax_category', '!=', False), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', required=True)
    currency_id = fields.Many2one('res.currency', required=True)
    use_gross = fields.Boolean('Use Gross as Base', default=True)
    manual_base = fields.Monetary('Custom Tax Base')
    base_amount = fields.Monetary('Taxable Base', compute='_compute_base', store=True)
    account_id = fields.Many2one('account.account', compute='_compute_tax_snapshot', store=True)
    category = fields.Selection([('wht', 'WHT'), ('stsp', 'Sales Tax / STSP')],
        compute='_compute_tax_snapshot', store=True)
    rate = fields.Float('Configured Rate (%)', compute='_compute_tax_snapshot', store=True, digits=(16, 6))
    calculation = fields.Char('Calculation', compute='_compute_tax_snapshot', store=True)
    amount = fields.Monetary('Deduction', compute='_compute_amount_tax', store=True)
    effective_rate = fields.Float('Effective Rate (%)', compute='_compute_effective_rate', digits=(16, 6))

    @api.depends('tax_id')
    def _compute_tax_snapshot(self):
        for line in self:
            tax = line.tax_id
            line.account_id = tax.account_id
            line.category = tax.payment_tax_category
            line.rate = abs(tax.amount)
            line.calculation = (tax.formula if tax and tax.amount_type == 'code' else tax.amount_type) or ''

    @api.depends('tax_id', 'base_amount', 'currency_id')
    def _compute_amount_tax(self):
        for line in self:
            if not line.tax_id or not line.currency_id:
                line.amount = 0
                continue
            values = line.tax_id.compute_all(line.base_amount, currency=line.currency_id,
                quantity=1, handle_price_include=False)
            line.amount = line.currency_id.round(abs(sum(t['amount'] for t in values['taxes'])))

    @api.depends('amount', 'base_amount')
    def _compute_effective_rate(self):
        for line in self:
            line.effective_rate = 100 * line.amount / line.base_amount if line.base_amount else 0

    def _validate_deduction(self):
        for line in self:
            if not line.category or not line.account_id or not line.account_id.active:
                raise ValidationError(_('Configure a deduction category and an active tax account on each tax.'))
            if line.company_id not in line.account_id.company_ids or line.tax_id.company_id != line.company_id:
                raise ValidationError(_('The deduction tax and account must belong to the payment company.'))
            if line.account_id.account_type != 'liability_current':
                raise ValidationError(_('Payment deductions require a current-liability tax account.'))
            if line.base_amount <= 0 or line.amount <= 0:
                raise ValidationError(_('Each deduction must have a positive taxable base and amount. Check zero-rate taxes.'))
            if line.tax_id.amount_type not in ('percent', 'code', 'fixed', 'division'):
                raise ValidationError(_('Use an individual deduction tax, not a tax group.'))


class PaymentTaxLine(models.Model):
    _name = 'optix.payment.tax.line'
    _inherit = 'optix.payment.tax.mixin'
    _description = 'Payment tax deduction'
    _check_company_auto = True

    payment_id = fields.Many2one('account.payment', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='payment_id.company_id', store=True, precompute=True)
    currency_id = fields.Many2one(related='payment_id.currency_id', store=True, precompute=True)

    @api.depends('use_gross', 'manual_base', 'payment_id.optix_gross_amount')
    def _compute_base(self):
        for line in self:
            line.base_amount = line.payment_id.optix_gross_amount if line.use_gross else line.manual_base

    @api.model_create_multi
    def create(self, vals_list):
        parents = self.env['account.payment'].browse([v['payment_id'] for v in vals_list])
        parents._optix_check_editable()
        records = super().create(vals_list)
        records.payment_id._optix_sync_net()
        return records

    def write(self, vals):
        self.payment_id._optix_check_editable()
        if 'payment_id' in vals:
            raise ValidationError(_('Deduction lines cannot be moved between payments.'))
        result = super().write(vals)
        self.payment_id._optix_sync_net()
        return result

    def unlink(self):
        payments = self.payment_id
        payments._optix_check_editable()
        result = super().unlink()
        payments._optix_sync_net()
        return result


class PaymentAdviceLine(models.Model):
    _name = 'optix.payment.advice.line'
    _description = 'Payment advice invoice/reference allocation'
    _check_company_auto = True

    payment_id = fields.Many2one('account.payment', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='payment_id.company_id', store=True, precompute=True)
    currency_id = fields.Many2one(related='payment_id.currency_id')
    invoice_id = fields.Many2one('account.move', check_company=True, ondelete='restrict',
        domain="[('move_type', '=', 'in_invoice'), ('company_id', '=', company_id)]")
    invoice_number = fields.Char('Invoice Number')
    invoice_date = fields.Date('Invoice Date')
    po_reference = fields.Char('P.O. / Bill Reference')
    pr_reference = fields.Char('PR No.')
    gross_amount = fields.Monetary('Gross Allocation')

    @api.model
    def _invoice_values(self, invoice):
        orders = invoice.invoice_line_ids.purchase_line_id.order_id
        return {'invoice_id': invoice.id, 'invoice_number': invoice.ref or invoice.name,
            'invoice_date': invoice.invoice_date, 'po_reference': ', '.join(orders.mapped('name')) or invoice.invoice_origin or invoice.name,
            'pr_reference': ', '.join(orders.approval_request_id.mapped('name'))}

    @api.onchange('invoice_id')
    def _onchange_invoice(self):
        if self.invoice_id:
            self.update(self._invoice_values(self.invoice_id))

    @api.model_create_multi
    def create(self, vals_list):
        self.env['account.payment'].browse([v['payment_id'] for v in vals_list])._optix_check_editable()
        return super().create(vals_list)

    def write(self, vals):
        self.payment_id._optix_check_editable()
        if 'payment_id' in vals:
            raise ValidationError(_('Advice lines cannot be moved between payments.'))
        return super().write(vals)

    def unlink(self):
        self.payment_id._optix_check_editable()
        return super().unlink()


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    optix_tax_payment = fields.Boolean('Payment Tax Deductions', copy=True, tracking=True)
    optix_gross_amount = fields.Monetary('Gross Amount', copy=True, tracking=True)
    optix_tax_line_ids = fields.One2many('optix.payment.tax.line', 'payment_id', string='Tax Deductions', copy=True)
    optix_advice_line_ids = fields.One2many('optix.payment.advice.line', 'payment_id', string='Invoice / PR References', copy=True)
    optix_wht_amount = fields.Monetary('WHT Amount', compute='_compute_optix_totals')
    optix_stsp_amount = fields.Monetary('Sales Tax / STSP Deduction', compute='_compute_optix_totals')
    optix_net_amount = fields.Monetary('Net Payable', compute='_compute_optix_totals')
    optix_journal_line_ids = fields.One2many(related='move_id.line_ids', string='Accounting Entries', readonly=True)
    optix_payee = fields.Char('Payee Name', tracking=True)
    optix_cheque_date = fields.Date('Cheque Date', tracking=True)

    @api.depends('optix_gross_amount', 'optix_tax_line_ids.amount', 'optix_tax_line_ids.category')
    def _compute_optix_totals(self):
        for pay in self:
            pay.optix_wht_amount = sum(pay.optix_tax_line_ids.filtered(lambda l: l.category == 'wht').mapped('amount'))
            pay.optix_stsp_amount = sum(pay.optix_tax_line_ids.filtered(lambda l: l.category == 'stsp').mapped('amount'))
            pay.optix_net_amount = pay.currency_id.round(pay.optix_gross_amount - pay.optix_wht_amount - pay.optix_stsp_amount)

    def _optix_check_editable(self):
        if any(p.state != 'draft' or p.move_id.state == 'posted' for p in self):
            raise UserError(_('Reset the payment to draft before changing tax or advice details.'))

    def _optix_sync_net(self):
        for pay in self.filtered(lambda p: p.optix_tax_payment and p.state == 'draft'):
            net = pay.optix_net_amount
            if net < 0:
                raise ValidationError(_('Tax deductions cannot exceed the gross amount.'))
            if pay.amount != net:
                super(AccountPayment, pay).write({'amount': net})
            elif pay.move_id and pay.move_id.state == 'draft':
                pay._synchronize_to_moves({'optix_tax_line_ids'})

    @api.onchange('optix_tax_payment', 'optix_gross_amount', 'optix_tax_line_ids')
    def _onchange_optix_tax(self):
        if self.optix_tax_payment:
            self.amount = self.optix_net_amount

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._optix_sync_net()
        return records

    def write(self, vals):
        protected = {'optix_tax_payment', 'optix_gross_amount', 'optix_tax_line_ids',
            'optix_advice_line_ids', 'optix_payee', 'optix_cheque_date'}
        if vals.get('optix_tax_payment') is False and self.optix_tax_line_ids:
            raise ValidationError(_('Remove deduction lines before disabling payment tax deductions.'))
        if protected.intersection(vals):
            self._optix_check_editable()
        if {'amount', 'currency_id', 'partner_id', 'partner_type', 'payment_type', 'date', 'journal_id'}.intersection(vals):
            self.filtered('optix_tax_payment')._optix_check_editable()
        if vals.get('state') in ('in_process', 'paid'):
            self._optix_validate()
        result = super().write(vals)
        self._optix_sync_net()
        return result

    def _optix_validate(self):
        for pay in self.filtered('optix_tax_payment'):
            if pay.payment_type != 'outbound' or pay.partner_type != 'supplier' or not pay.partner_id:
                raise ValidationError(_('Tax deductions are supported on outgoing supplier payments.'))
            if not pay.destination_account_id:
                raise ValidationError(_('Configure a payable account on the supplier before posting.'))
            if not pay.outstanding_account_id:
                raise ValidationError(_('Set an outstanding payments account on the journal payment method before posting tax deductions.'))
            if pay.optix_gross_amount <= 0 or pay.optix_net_amount <= 0:
                raise ValidationError(_('Gross and net payable amounts must be positive.'))
            if pay.currency_id.compare_amounts(pay.amount, pay.optix_net_amount):
                raise ValidationError(_('The payment amount must equal gross less all deductions.'))
            pay.optix_tax_line_ids._validate_deduction()
            if len(pay.optix_tax_line_ids.tax_id) != len(pay.optix_tax_line_ids):
                raise ValidationError(_('Each tax may only occur once per payment.'))
            if pay.optix_advice_line_ids:
                if pay.currency_id.compare_amounts(sum(pay.optix_advice_line_ids.mapped('gross_amount')), pay.optix_gross_amount):
                    raise ValidationError(_('Advice gross allocations must total the payment gross amount.'))
                for line in pay.optix_advice_line_ids:
                    if line.gross_amount <= 0:
                        raise ValidationError(_('Advice allocations must be positive.'))
                    if line.invoice_id and (line.invoice_id.move_type != 'in_invoice' or
                            line.invoice_id.partner_id.commercial_partner_id != pay.partner_id.commercial_partner_id):
                        raise ValidationError(_('Advice bills must belong to the payment supplier.'))

    def action_post(self):
        self._optix_sync_net()
        self._optix_validate()
        return super().action_post()

    def _prepare_move_lines_per_type(self, write_off_line_vals=None, force_balance=None):
        if self.optix_tax_payment:
            write_off_line_vals = [{
                'name': '%s: %s' % (line.category.upper(), line.tax_id.name),
                'account_id': line.account_id.id, 'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id, 'amount_currency': -line.amount,
                'balance': self.currency_id._convert(-line.amount, self.company_id.currency_id, self.company_id, self.date),
            } for line in self.optix_tax_line_ids]
            force_balance = None
        return super()._prepare_move_lines_per_type(write_off_line_vals, force_balance)

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        return super()._get_trigger_fields_to_synchronize() + ('optix_tax_line_ids', 'optix_gross_amount', 'optix_tax_payment')

    def _optix_advice_values(self):
        self.ensure_one()
        if not self.optix_tax_payment:
            raise UserError(_('Use Payment Tax Deductions for this advice. Historical payments retain their original receipts.'))
        self._optix_validate()
        if self.move_id.state == 'posted':
            liquidity, counterpart, other = self._seek_for_lines()
            if (self.currency_id.compare_amounts(-sum(liquidity.mapped('amount_currency')), self.amount)
                    or self.currency_id.compare_amounts(sum(counterpart.mapped('amount_currency')), self.optix_gross_amount)):
                raise UserError(_('The journal entry differs from the payment advice. Review the entry before printing.'))
            for account in self.optix_tax_line_ids.account_id:
                recorded = -sum(other.filtered(lambda l: l.account_id == account).mapped('amount_currency'))
                expected = sum(self.optix_tax_line_ids.filtered(lambda l: l.account_id == account).mapped('amount'))
                if self.currency_id.compare_amounts(recorded, expected):
                    raise UserError(_('The posted tax entries differ from the deduction details. Review them before printing.'))
        return {'gross': self.optix_gross_amount, 'wht': self.optix_wht_amount,
            'stsp': self.optix_stsp_amount, 'net': self.amount}


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_next_sequence_format(self):
        """Keep imported fiscal labels from blocking NEW tax-payment vouchers.

        Preserve historical entries, and retain core sequence locking/uniqueness.
        Odoo normally resets by entry date, but imported entries can already have
        a date in the current period while retaining an old fiscal-year label.
        """
        fmt, values = super()._get_next_sequence_format()
        if not self.origin_payment_id.optix_tax_payment:
            return fmt, values
        reset = self._deduce_sequence_number_reset(fmt.format(**values))
        start, end, forced_start, forced_end = self._get_sequence_date_range(reset)
        expected = {
            'year': self._truncate_year_to_length(forced_start or start.year, values['year_length']),
            'year_end': self._truncate_year_to_length(forced_end or end.year, values['year_end_length']),
        }
        if any(values[key] and values[key] != value for key, value in expected.items()):
            values.update(expected, seq=0)
        return fmt, values
