from odoo import models, fields

class BudgetWarningWizard(models.TransientModel):
    _name = 'budget.warning.wizard'
    _description = 'Budget Warning Wizard'

    order_id = fields.Many2one('purchase.order')
    message = fields.Text()

    def action_proceed(self):
        self.ensure_one()
        return self.order_id.with_context(skip_budget_check=True).button_approve()

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}