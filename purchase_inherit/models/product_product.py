from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("default_code"):
                vals["default_code"] = self.env["ir.sequence"].next_by_code(
                    "product.template.sequence"
                ) or "New"
        return super().create(vals_list)

    analytic_gl_id = fields.Many2one(
        "account.analytic.account",
        string="GL",
        help="Analytic account used as the GL account.",
        domain=[("plan_id.name", "ilike", "GL")],
    )
    
    warrenty_time = fields.Integer(string="Warrent")
    asset_tag_no = fields.Char(string="Asset Tag No.")
    
