from odoo import models, fields, api, _ 

class BudgetAnalytics(models.Model):
    _inherit="budget.analytic"

    configuration = fields.Selection([
        ('restrict','Restrict'),
        ('allow','Allow'),
        ('warning','Show only warning'),
    ],string="Configuration", required=True)
    

class BudgetLine(models.Model):
    _inherit="budget.line"
    
    product_id = fields.Many2one('product.template', string="Product", required=False)