from odoo import models, fields, api, _ 

class BudgetAnalytics(models.Model):
    _inherit="budget.analytic"

    configuration = fields.Selection([
        ('restrict','Restrict'),
        ('allow','Allow'),
        ('warning','Show only warning'),
    ],string="Configuration", required=True)