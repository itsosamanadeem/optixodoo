from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    analytic_gl_id = fields.Many2one(
        "account.analytic.account",
        string="GL",
        help="Analytic account used as the GL account.",
        domain=[("plan_id.name", "ilike", "GL")],
    )