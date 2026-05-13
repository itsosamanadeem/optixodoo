from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    product_default_code = fields.Char(
        string="Product Default Code",
        compute="_compute_product_info_fields",
    )
    asset_tag_no = fields.Char(
        string="Asset Tag No.",
        compute="_compute_product_info_fields",
    )

    def _compute_product_info_fields(self):
        for picking in self:
            if "move_ids_without_package" in picking._fields:
                moves = picking.move_ids_without_package
            elif "move_ids" in picking._fields:
                moves = picking.move_ids
            elif "move_lines" in picking._fields:
                moves = picking.move_lines
            else:
                moves = self.env["stock.move"]
            tags = moves.mapped("product_id.asset_tag_no")
            default_codes = moves.mapped("product_id.default_code")
            picking.asset_tag_no = ", ".join(sorted({tag for tag in tags if tag}))
            picking.product_default_code = ", ".join(
                sorted({code for code in default_codes if code})
            )
