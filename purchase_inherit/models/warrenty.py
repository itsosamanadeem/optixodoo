from datetime import timedelta

from odoo import api, fields, models

class ProductWarrenty(models.Model):
    _inherit = "stock.lot"

    warrenty_start = fields.Date(string="Warrenty Start")
    warrenty_end = fields.Date(string="Warrenty End")

    warrenty_status = fields.Selection([
        ("in_warrenty", "In Warrenty"),
        ("no_warrenty", "Not in Warrenty"),
    ], string="Warrenty Status", compute="_compute_warrenty_status", store=True)

    @api.depends("warrenty_start", "warrenty_end")
    def _compute_warrenty_status(self):
        today = fields.Date.context_today(self)
        for lot in self:
            if lot.warrenty_start and lot.warrenty_end and lot.warrenty_start <= today <= lot.warrenty_end:
                lot.warrenty_status = "in_warrenty"
            else:
                lot.warrenty_status = "no_warrenty"

    @api.model_create_multi
    def create(self, vals_list):
        lots = super().create(vals_list)
        for lot in lots.filtered(lambda l: l.product_id and l.product_id.warrenty_time):
            if not lot.warrenty_start:
                lot.warrenty_start = fields.Date.context_today(lot)
            if not lot.warrenty_end and lot.warrenty_start:
                lot.warrenty_end = lot.warrenty_start + timedelta(days=lot.product_id.warrenty_time)
        return lots
