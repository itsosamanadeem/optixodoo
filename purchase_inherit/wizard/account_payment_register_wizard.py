from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    optix_tax_payment = fields.Boolean('Payment Tax Deductions')
    optix_gross_amount = fields.Monetary('Gross Settlement', compute='_compute_optix_gross', store=True, readonly=False)
    price_unit = fields.Float('Untaxed Amount', compute='_compute_amount_untaxed')
    amount_before_tax = fields.Monetary('Base Amount', related='optix_gross_amount')
    income_tax_ids = fields.One2many('account.payment.register.tax.line', 'wizard_id', string='Tax Deductions')
    total_taxed_amount = fields.Monetary('Total Deductions', compute='_compute_total_taxed_amount')

    @api.depends('line_ids.move_id.amount_untaxed')
    def _compute_amount_untaxed(self):
        for wizard in self:
            wizard.price_unit = sum(wizard.line_ids.move_id.mapped('amount_untaxed'))

    @api.depends('currency_id', 'payment_date', 'source_amount', 'source_amount_currency', 'source_currency_id')
    def _compute_optix_gross(self):
        for wizard in self:
            if wizard.currency_id and wizard.source_currency_id and wizard.payment_date:
                wizard.optix_gross_amount = wizard.source_currency_id._convert(
                    wizard.source_amount_currency, wizard.currency_id, wizard.company_id, wizard.payment_date)
            else:
                wizard.optix_gross_amount = wizard.source_amount

    @api.depends('income_tax_ids.amount')
    def _compute_total_taxed_amount(self):
        for wizard in self:
            wizard.total_taxed_amount = sum(wizard.income_tax_ids.mapped('amount'))

    @api.depends('can_edit_wizard', 'source_amount', 'source_amount_currency', 'source_currency_id',
        'company_id', 'currency_id', 'payment_date', 'installments_mode', 'optix_tax_payment',
        'optix_gross_amount', 'income_tax_ids.amount')
    def _compute_amount(self):
        super()._compute_amount()
        for wizard in self:
            if wizard.optix_tax_payment:
                wizard.amount = wizard.currency_id.round(wizard.optix_gross_amount - wizard.total_taxed_amount)

    @api.onchange('optix_tax_payment')
    def _onchange_optix_tax_payment(self):
        if self.optix_tax_payment:
            self.payment_difference_handling = 'open'
            if self.can_group_payments:
                self.group_payment = True

    def _optix_validate_wizard(self):
        self.ensure_one()
        if not self.optix_tax_payment:
            return
        if self.payment_type != 'outbound' or self.partner_type != 'supplier':
            raise ValidationError(_('Tax deductions require an outgoing supplier payment.'))
        if not self.can_edit_wizard or (len(self.line_ids) > 1 and not self.group_payment) or len(self.batches) != 1:
            raise ValidationError(_('Group bills for one supplier, currency and payable account, or register them separately.'))
        if self.payment_difference_handling != 'open' or self.early_payment_discount_mode:
            raise ValidationError(_('Use Keep Open for the payment difference. Tax deductions settle the gross balance automatically; early-payment discounts cannot be combined.'))
        if self.optix_gross_amount <= 0 or self.amount <= 0:
            raise ValidationError(_('Gross and net amounts must be positive.'))
        available = self.source_currency_id._convert(self.source_amount_currency,
            self.currency_id, self.company_id, self.payment_date)
        if self.currency_id.compare_amounts(self.optix_gross_amount, available) > 0:
            raise ValidationError(_('Gross settlement cannot exceed the selected outstanding balance.'))
        if self.currency_id.compare_amounts(self.amount, self.optix_gross_amount - self.total_taxed_amount):
            raise ValidationError(_('Net payment must equal gross less deductions. Change Gross Settlement for a partial payment.'))
        self.income_tax_ids._validate_deduction()

    def _create_payment_vals_from_wizard(self, batch_result):
        self._optix_validate_wizard()
        vals = super()._create_payment_vals_from_wizard(batch_result)
        if not self.optix_tax_payment:
            return vals
        vals.update(optix_tax_payment=True, optix_gross_amount=self.optix_gross_amount,
            optix_tax_line_ids=[Command.create({'tax_id': line.tax_id.id,
                'use_gross': line.use_gross, 'manual_base': line.manual_base}) for line in self.income_tax_ids])
        # Allocate partial gross settlements proportionally to the selected bill residuals.
        bills = batch_result['lines'].move_id.sorted('id')
        weights = []
        for bill in bills:
            selected = batch_result['lines'].filtered(lambda l: l.move_id == bill)
            weights.append(abs(sum(selected.mapped('amount_residual_currency'))))
        total = sum(weights)
        remaining = self.optix_gross_amount
        references = []
        for index, (bill, weight) in enumerate(zip(bills, weights)):
            allocation = remaining if index == len(bills) - 1 else self.currency_id.round(self.optix_gross_amount * weight / total)
            remaining -= allocation
            if self.currency_id.is_zero(allocation):
                continue
            info = self.env['optix.payment.advice.line']._invoice_values(bill)
            info['gross_amount'] = allocation
            references.append(Command.create(info))
        vals['optix_advice_line_ids'] = references
        return vals

    def _create_payments(self):
        self._optix_validate_wizard()
        return super()._create_payments()


class VendorPaymentTaxLine(models.TransientModel):
    _name = 'account.payment.register.tax.line'
    _inherit = 'optix.payment.tax.mixin'
    _description = 'Payment Register Tax Deduction'
    _check_company_auto = True

    wizard_id = fields.Many2one('account.payment.register', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='wizard_id.company_id', store=True, precompute=True)
    currency_id = fields.Many2one(related='wizard_id.currency_id', store=True, precompute=True)

    @api.depends('use_gross', 'manual_base', 'wizard_id.optix_gross_amount')
    def _compute_base(self):
        for line in self:
            line.base_amount = line.wizard_id.optix_gross_amount if line.use_gross else line.manual_base
