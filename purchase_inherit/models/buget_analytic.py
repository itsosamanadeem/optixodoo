from odoo import models, fields, api, _ 

class BudgetAnalytics(models.Model):
    _inherit="budget.analytic"

    configuration = fields.Selection([
        ('restrict','Restrict'),
        ('allow','Allow'),
        ('warning','Show only warning'),
    ],string="Configuration", required=True, default='warning',)

    def action_open_budget_line_filter(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Filter Budget Lines'),
            'res_model': 'budget.line.filter.wizard.purchase',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_budget_analytic_id': self.id,
            },
        }
    

class BudgetLine(models.Model):
    _inherit="budget.line"
    
    product_id = fields.Many2one('product.template', string="Product", required=False)
