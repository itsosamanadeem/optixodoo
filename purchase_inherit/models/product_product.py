from odoo import api, fields, models #type: ignore
from odoo.exceptions import UserError #type: ignore


class ProductTemplate(models.Model):
    _inherit = ["product.template",'mail.thread', 'mail.activity.mixin']

    analytic_gl_id = fields.Many2one(
        "account.analytic.account",
        string="GL",
        help="Analytic account used as the GL account.",
        domain=[("plan_id.name", "ilike", "GL")],
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("default_code"):
                vals["default_code"] = self.env["ir.sequence"].next_by_code(
                    "product.template.sequence"
                ) or "New"
        return super().create(vals_list)

    warrenty_time = fields.Integer(string="Warrent", tracking=True)
    asset_tag_no = fields.Char(string="Asset Tag No.", tracking=True)

