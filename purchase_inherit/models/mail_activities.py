from odoo import api, models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore


class MailActivities(models.Model):
    _inherit = "mail.activity"

    @api.depends("user_id", "approval_request_id.approver_ids.user_id")
    def _compute_approver_id(self):
        for activity in self:
            approvers = activity.approval_request_id.approver_ids.filtered(
                lambda approver: activity.user_id == approver.user_id
            )
            activity.approver_id = approvers[:1]

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
