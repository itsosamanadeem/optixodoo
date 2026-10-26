from odoo import models


class ApprovalApprover(models.Model):
    _inherit = 'approval.approver'

    _unique_request_user = None

    def init(self):
        super().init()
        self.env.cr.execute("""
            ALTER TABLE approval_approver
            DROP CONSTRAINT IF EXISTS approval_approver_unique_request_user
        """)
