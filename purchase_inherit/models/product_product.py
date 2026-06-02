from odoo import api, fields, models #type: ignore
from odoo.exceptions import UserError #type: ignore


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

    warrenty_time = fields.Integer(string="Warrent")
    asset_tag_no = fields.Char(string="Asset Tag No.")
    
