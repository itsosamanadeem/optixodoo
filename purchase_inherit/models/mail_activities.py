from odoo import models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore


class MailActivities(models.Model):
    _inherit = "mail.activity"

    def _check_can_complete_activity(self):
        if self.env.is_superuser():
            return
        unauthorized = self.filtered(lambda act: act.user_id and act.user_id != self.env.user)
        if unauthorized:
            raise UserError(_("You can only complete activities assigned to you."))

    def action_feedback(self, feedback=False, attachment_ids=None):
        self._check_can_complete_activity()
        return super().action_feedback(feedback=feedback, attachment_ids=attachment_ids)

    def action_done(self):
        self._check_can_complete_activity()
        return super().action_done()

    def action_done_schedule_next(self):
        self._check_can_complete_activity()
        return super().action_done_schedule_next()
