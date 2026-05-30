from odoo import fields, models, api # type: ignore

class AccountTax(models.Model):
    _inherit = "account.tax"
    
    is_income_tax = fields.Boolean(string="Is Income Tax", default=False)
    account_id = fields.Many2one("account.account", string="Account", store=True)