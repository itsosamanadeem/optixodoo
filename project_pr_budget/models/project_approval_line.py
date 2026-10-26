from odoo import fields, models


class ProjectApprovalLine(models.Model):
    _name = "project.approval.line"
    _description = "Project Approval Line"
    _order = "sequence, id"

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    approval_level_id = fields.Many2one(
        "ml.approval.level",
        string="Approval Level",
        required=True,
        readonly=True,
    )
    sequence = fields.Integer(readonly=True)
    user_ids = fields.Many2many(
        "res.users",
        "project_approval_line_user_rel",
        "line_id",
        "user_id",
        string="Approvers",
        readonly=True,
    )
    status = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="waiting",
        required=True,
        readonly=True,
    )
    approved_by_id = fields.Many2one(
        "res.users",
        string="Approved/Rejected By",
        readonly=True,
    )
    approved_date = fields.Datetime(string="Action Date", readonly=True)
    comments = fields.Text(readonly=True)
