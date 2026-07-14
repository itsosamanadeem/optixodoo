from odoo import fields, models, _


class BudgetLineFilterWizard(models.TransientModel):
    _name = 'budget.line.filter.wizard'
    _description = 'Budget Line Combination Filter'

    budget_id = fields.Many2one(
        'budget.budget',
        string='Budget',
        required=True,
        readonly=True,
    )
    general_budget_id = fields.Many2one(
        'account.budget.post',
        string='Budgetary Position',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    paid_date = fields.Date(string='Paid Date')
    planned_amount_operator = fields.Selection(
        selection=[
            ('=', 'Equals'),
            ('>=', 'Greater Than or Equal'),
            ('<=', 'Less Than or Equal'),
        ],
        string='Planned Amount Filter',
    )
    planned_amount = fields.Float(string='Planned Amount', digits=0)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        readonly=True,
    )

    def _get_filter_domain(self):
        self.ensure_one()
        domain = [('budget_id', '=', self.budget_id.id)]

        if self.general_budget_id:
            domain.append(('general_budget_id', '=', self.general_budget_id.id))
        if self.analytic_account_id:
            domain.append(('analytic_account_id', '=', self.analytic_account_id.id))
        if self.date_from:
            domain.append(('date_from', '=', self.date_from))
        if self.date_to:
            domain.append(('date_to', '=', self.date_to))
        if self.paid_date:
            domain.append(('paid_date', '=', self.paid_date))
        if self.planned_amount_operator:
            domain.append((
                'planned_amount',
                self.planned_amount_operator,
                self.planned_amount,
            ))

        return domain

    def action_apply_filters(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Filtered Budget Lines'),
            'res_model': 'budget.lines',
            'view_mode': 'list,form',
            'domain': self._get_filter_domain(),
            'context': {
                'default_budget_id': self.budget_id.id,
                'default_date_from': self.budget_id.date_from,
                'default_date_to': self.budget_id.date_to,
            },
        }
