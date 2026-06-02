from odoo import models, fields, api, _ #type: ignore

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    serial_no = fields.Char(
        string="Serial Number",
    )

    # @api.depends("product_id")
    # def _compute_asset_tag_no(self):
    #     for move_line in self:
    #         move_line.asset_tag_no = move_line.product_id.asset_tag_no or ""
