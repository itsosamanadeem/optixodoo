from odoo import api, fields, models


class RepairOrder(models.Model):
    _inherit = ["repair.order",'mail.thread', 'mail.activity.mixin']

    warrenty_status = fields.Selection(
        related="lot_id.warrenty_status",
        string="Warrenty Status",
        readonly=True,
        tracking=True,
    )

    @api.onchange("lot_id")
    def _onchange_lot_id_set_under_warranty(self):
        for rec in self:
            if not rec.lot_id:
                rec.under_warranty = False
                continue
            rec.under_warranty = rec.lot_id.warrenty_status == "in_warrenty"
