from odoo import fields, models #type: ignore


class HrDepartment(models.Model):
    _inherit = ["hr.department",'mail.thread', 'mail.activity.mixin']

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Cost Center",
        help="Analytic account used as the department cost center.",
        domain=[("plan_id.name", "ilike", "Cost Center")],
        tracking=True,
    )

    analytic_city_id = fields.Many2one(
        "account.analytic.account",
        string="City",
        help="Analytic city used as the department city center.",
        domain=[("plan_id.name", "ilike", "City")],
        tracking=True,
    )

    location_id = fields.Many2one(
        "stock.location",
        string="Department Location",
        help="Optional stock location associated with this department.",
        tracking=True,
    )
