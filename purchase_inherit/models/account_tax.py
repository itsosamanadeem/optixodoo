from odoo import fields, models, api # type: ignore

class AccountTax(models.Model):
    _inherit = ["account.tax",'mail.thread', 'mail.activity.mixin']

    is_income_tax = fields.Boolean(string="Is Income Tax", default=False, tracking=True)
    account_id = fields.Many2one("account.account", string="Account", store=True, tracking=True)