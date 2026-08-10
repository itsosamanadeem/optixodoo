from odoo import fields, models, api , _# type: ignore
from odoo.exceptions import UserError # type: ignore
from odoo.tools import frozendict, OrderedSet # type: ignore
from odoo.tools.misc import clean_context # type: ignore

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    payment_difference_handling = fields.Selection(
        string="Payment Difference Handling",
        selection=[('open', 'Keep open'), ('reconcile', 'Mark as fully paid'), ('withhold','Tax Entries')],
        compute='_compute_payment_difference_handling',
        store=True,
        readonly=False,
        tracking=True,
    )
    price_unit = fields.Float(
        string="Untaxed Amount",
        copy=False,
        readonly=True,
        compute="_compute_amount_untaxed",
        tracking=True,
    )
    amount_before_tax = fields.Monetary(
        string="Base Amount",
        currency_field="currency_id",
        copy=False,
        compute="_compute_amount_before_tax",
        tracking=True,
    )
    income_tax_ids = fields.One2many(
        "account.payment.register.tax.line",
        "wizard_id",
        string="Income Tax Line",
        tracking=True,
    )
    total_taxed_amount = fields.Float(string="Total Taxed Amount", readonly=True, compute="_compute_total_taxed_amount", store=True, tracking=True)

    @api.depends("income_tax_ids", "income_tax_ids.amount")
    def _compute_total_taxed_amount(self):
        for wizard in self:
            wizard.total_taxed_amount = sum(wizard.income_tax_ids.mapped("amount"))

    @api.depends("line_ids", "line_ids.move_id", "line_ids.move_id.price_unit")
    def _compute_amount_untaxed(self):
        for wizard in self:
            invoices = wizard.line_ids.mapped("move_id")
            wizard.price_unit = sum(invoices.mapped("amount_untaxed"))

    @api.depends("price_unit", "source_amount_currency", "source_amount")
    def _compute_amount_before_tax(self):
        for wizard in self:
            wizard.amount_before_tax = wizard.price_unit

    @api.depends(
        'can_edit_wizard',
        'source_amount',
        'source_amount_currency',
        'source_currency_id',
        'company_id',
        'currency_id',
        'payment_date',
        'installments_mode',
        'total_taxed_amount',
    )
    def _compute_amount(self):
        res = super(AccountPaymentRegister, self)._compute_amount()
        for wizard in self:
            base_amount = wizard.source_amount or 0.0
            total_tax = wizard.total_taxed_amount
            wizard.amount = base_amount - total_tax
        return res

    @api.depends('early_payment_discount_mode')
    def _compute_payment_difference_handling(self):
        res = super(AccountPaymentRegister, self)._compute_payment_difference_handling()
        for wizard in self:
            if len(wizard.income_tax_ids) > 0:
                wizard.payment_difference_handling = 'withhold'
                wizard.writeoff_is_exchange_account = True
        return res

    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        move = self.line_ids[:1].move_id
        move_id = move.id
        if not move_id:
            return res
        for tax_line in self.income_tax_ids:
            if not tax_line.account_id:
                continue
            self.env['account.move.line'].create({
                'name': tax_line.tax_id.name,
                'account_id': tax_line.account_id.id,
                'debit': 0.0,
                'credit': tax_line.amount,
                'move_id': move_id,
            })
        return res
    # @api.onchange("income_tax_ids", "income_tax_ids.tax_id", "amount_before_tax")
    # def _onchange_income_tax_ids_recompute_amount(self):
    #     for wizard in self:
    #         if not wizard.income_tax_ids:
    #             base_amount = wizard.amount_before_tax or wizard.amount or 0.0
    #             wizard.amount = base_amount - sum(abs(x) for x in wizard.income_tax_ids.mapped("amount"))

    # def _create_payment_vals_from_wizard(self, batch_result):
    #     payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)
    #     for wizard in self:
    #         if not wizard.income_tax_ids:
    #             continue

    #         missing_accounts = wizard.income_tax_ids.filtered(lambda l: not l.account_id)
    #         if missing_accounts:
    #             raise UserError(_("Please configure an account on each selected tax line."))

    #         # Replace the default single write-off line with tax-based GL split lines.
    #         payment_vals['write_off_line_vals'] = []
    #         for tax_line in wizard.income_tax_ids:
    #             payment_vals['write_off_line_vals'].append({
    #                 'name': tax_line.tax_id.name,
    #                 'account_id': tax_line.account_id.id,
    #                 'partner_id': wizard.partner_id.id,
    #                 'currency_id': wizard.currency_id.id,
    #                 'amount_currency': abs(tax_line.amount),
    #                 'balance': wizard.currency_id._convert(abs(tax_line.amount), wizard.company_id.currency_id, wizard.company_id, wizard.payment_date),
    #             })
    #     # raise UserError(str(payment_vals))
    #     return payment_vals

    # def _create_payments(self):
    #     self.ensure_one()
    #     batches = []
    #     # Skip batches that are not valid (bank account not setup or not trusted but required)
    #     for batch in self.batches:
    #         batch_account = self._get_batch_account(batch)
    #         if self.require_partner_bank_account and (not batch_account or not batch_account.allow_out_payment):
    #             continue
    #         batches.append(batch)

    #     if not batches:
    #         raise UserError(_(
    #             "To record payments with %(payment_method)s, the recipient bank account must be manually validated. You should go on the partner bank account in order to validate it.",
    #             payment_method=self.payment_method_line_id.name,
    #         ))

    #     first_batch_result = batches[0]
    #     edit_mode = self.can_edit_wizard and (len(first_batch_result['lines']) == 1 or self.group_payment)
    #     to_process = []

    #     if edit_mode:
    #         payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
    #         to_process_values = {
    #             'create_vals': payment_vals,
    #             'to_reconcile': first_batch_result['lines'],
    #             'batch': first_batch_result,
    #         }

    #         # Force the rate during the reconciliation to put the difference directly on the
    #         # exchange difference.
    #         if self.writeoff_is_exchange_account and self.currency_id == self.company_currency_id:
    #             total_batch_residual = sum(first_batch_result['lines'].mapped('amount_residual_currency'))
    #             to_process_values['rate'] = abs(total_batch_residual / self.amount) if self.amount else 0.0
    #         elif self.payment_difference_handling == 'reconcile' and self.currency_id == self.company_currency_id:
    #             # total_batch_residual = sum(first_batch_result['lines'].mapped('amount_residual_currency'))
    #             to_process_values['rate'] = 0.0

    #         to_process.append(to_process_values)
    #     else:
    #         if not self.group_payment:
    #             # Don't group payments: Create one batch per move.
    #             lines_to_pay = self._get_total_amounts_to_pay(batches)['lines'] if self.installments_mode in ('next', 'overdue', 'before_date') else self.line_ids
    #             new_batches = []
    #             for batch_result in batches:
    #                 sub_batches = {}
    #                 for line in batch_result['lines']:
    #                     if line not in lines_to_pay:
    #                         continue
    #                     if line.move_id.id in sub_batches:
    #                         sub_batches[line.move_id.id]['lines'] += line
    #                     else:
    #                         sub_batches[line.move_id.id] = {
    #                             **batch_result,
    #                             'payment_values': {
    #                                 **batch_result['payment_values'],
    #                                 'payment_type': 'inbound' if line.balance > 0 else 'outbound'
    #                             },
    #                             'lines': line,
    #                         }
    #                 new_batches.extend(sub_batches.values())
    #             batches = new_batches

    #         for batch_result in batches:
    #             to_process.append({
    #                 'create_vals': self._create_payment_vals_from_batch(batch_result),
    #                 'to_reconcile': batch_result['lines'],
    #                 'batch': batch_result,
    #             })

    #     lines = sum((batch_result['lines'] for batch_result in batches), self.env['account.move.line'])
    #     from_sibling_companies = self._from_sibling_companies(lines)
    #     if from_sibling_companies and lines.company_id.root_id not in self.env.companies: #type: ignore
    #         # Payment made for sibling companies, we don't want to redirect to the payments
    #         # to avoid access error, as it will be created as parent company.
    #         self.env(context={**self.env.context, "dont_redirect_to_payments": True})

    #     wizard = self.sudo() if from_sibling_companies else self

    #     # Prevent default_ context keys to interfere with account.payment context (eg: ``default_partner_bank_id``
    #     # transfered from ``account.payment.register`` wizard to ``account.payment`` creation.
    #     payments = wizard.with_context(clean_context(self.env.context))._init_payments(to_process, edit_mode=edit_mode)

    #     # raise UserError(str(to_process))
    #     wizard._post_payments(to_process, edit_mode=edit_mode)
    #     wizard._reconcile_payments(to_process, edit_mode=edit_mode)
    #     return payments.sudo(flag=False)

class VendorPaymentTaxLine(models.TransientModel):
    _name = "account.payment.register.tax.line"
    _description = "Payment Register Income Tax Line"


    wizard_id = fields.Many2one(
        "account.payment.register",
        string="Payment Register Wizard",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    tax_id = fields.Many2one("account.tax", string="Tax", tracking=True)
    amount = fields.Float(string="Amount", compute="_compute_amount_tax", store=True, tracking=True)

    account_id = fields.Many2one("account.account", string="Account", related="tax_id.account_id", store=True, readonly=True, tracking=True)

    @api.depends(
        "tax_id",
        "wizard_id.amount_before_tax",
        "wizard_id.price_unit",
        "wizard_id.source_amount_currency",
        "wizard_id.currency_id",
        "wizard_id.partner_id",
    )
    def _compute_amount_tax(self):
        for line in self:
            if not line.tax_id or not line.wizard_id:
                line.amount = 0.0
                continue

            base_amount = line.wizard_id.source_amount_currency
            tax_data = line.tax_id.compute_all(
                base_amount,
                currency=line.wizard_id.currency_id,
                quantity=1.0,
                partner=line.wizard_id.partner_id,
            )
            tax_amount = tax_data.get("total_included", 0.0) - tax_data.get("total_excluded", 0.0)
            tax_amount = line.wizard_id.currency_id.round(tax_amount) if line.wizard_id.currency_id else tax_amount
            line.amount = abs(tax_amount)
