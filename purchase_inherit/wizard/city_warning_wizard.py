from odoo import models, fields
from odoo.exceptions import UserError


class CityWarningWizard(models.TransientModel):
    _name = 'city.warning.wizard'
    _description = 'City Warning Wizard'

    request_id = fields.Many2one('approval.request')
    message = fields.Text()

    def action_proceed(self):
        self.ensure_one()

        if not self.request_id:
            raise UserError("No request found for this wizard.")

        return self.request_id.with_context(skip_city_check=True).action_confirm()

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}