from odoo import fields, models, _


class BudgetLineFilterWizard(models.TransientModel):
    _name = 'budget.line.filter.wizard.purchase'
    _description = 'Budget Line Combination Filter'

    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Budget',
        required=True,
        readonly=True,
        tracking=True,
    )
    account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        domain=[("plan_id.name", "ilike", "Cost Center")],
        tracking=True,
    )
    x_plan6_id = fields.Many2one(
        'account.analytic.account',
        string='City',
        domain=[("plan_id.name", "ilike", "City")],
        tracking=True,
    )
    x_plan8_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic GL',
        domain=[("plan_id.name", "ilike", "GL")],
        tracking=True,
    )
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        tracking=True,
    )
    date_from = fields.Date(string='Start Date', tracking=True)
    date_to = fields.Date(string='End Date', tracking=True)
    budget_amount_operator = fields.Selection(
        selection=[
            ('=', 'Equals'),
            ('>=', 'Greater Than or Equal'),
            ('<=', 'Less Than or Equal'),
        ],
        string='Budget Amount Filter',
        tracking=True,
    )
    budget_amount = fields.Float(string='Budget Amount', tracking=True)

    def _get_filter_domain(self):
        self.ensure_one()
        domain = [('budget_analytic_id', '=', self.budget_analytic_id.id)]

        if self.account_id:
            domain.append(('account_id', '=', self.account_id.id))
        if self.x_plan6_id:
            domain.append(('x_plan6_id', '=', self.x_plan6_id.id))
        if self.x_plan8_id:
            domain.append(('x_plan8_id', '=', self.x_plan8_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.date_from:
            domain.append(('date_from', '=', self.date_from))
        if self.date_to:
            domain.append(('date_to', '=', self.date_to))
        if self.budget_amount_operator:
            domain.append((
                'budget_amount',
                self.budget_amount_operator,
                self.budget_amount,
            ))

        return domain

    def action_apply_filters(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Filtered Budget Lines'),
            'res_model': 'budget.line',
            'view_mode': 'list,form',
            'domain': self._get_filter_domain(),
            'context': {
                'default_budget_analytic_id': self.budget_analytic_id.id,
            },
        }
