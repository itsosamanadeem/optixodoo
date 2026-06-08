from odoo import fields, models #type: ignore


class HrDepartment(models.Model):
    _inherit = "hr.department"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Cost Center",
        help="Analytic account used as the department cost center.",
        domain=[("plan_id.name", "ilike", "Cost Center")],
    )
    
    analytic_city_id = fields.Many2one(
        "account.analytic.account",
        string="City",
        help="Analytic city used as the department city center.",
        domain=[("plan_id.name", "ilike", "City")],
    )
    
    location_id = fields.Many2one(
        "stock.location",
        string="Department Location",
        help="Stock location associated with this department for internal transfers.",
    )