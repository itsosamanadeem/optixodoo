from odoo import fields, models


class AccountTax(models.Model):
    _inherit = ['account.tax', 'mail.thread', 'mail.activity.mixin']

    is_income_tax = fields.Boolean(string='Is Income Tax', default=False, tracking=True)
    account_id = fields.Many2one('account.account', string='Payment Deduction Account',
        check_company=True, tracking=True)
    payment_tax_category = fields.Selection([('wht', 'WHT'), ('stsp', 'Sales Tax / STSP')],
        string='Payment Deduction Category', tracking=True,
        help='Only withholding deductions belong here. Normal invoice sales tax stays on the bill.')
