from odoo import models #type: ignore


class StockMove(models.Model):
    _inherit = ["stock.move",'mail.thread', 'mail.activity.mixin']

    def action_open_serial_import_wizard(self):
        self.ensure_one()
        return {
            "name": "Import Serial Numbers",
            "type": "ir.actions.act_window",
            "res_model": "stock.serial.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_move_id": self.id,
            },
        }
