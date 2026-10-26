from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProjectProject(models.Model):
    _inherit = "project.project"

    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("under_approval", "Under Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Status",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    approval_group_id = fields.Many2one(
        "ml.approval.group",
        string="Approval Group",
        tracking=True,
        copy=False,
    )
    current_approval_level_id = fields.Many2one(
        "ml.approval.level",
        string="Current Approval Level",
        compute="_compute_current_approval_level_id",
        store=True,
        tracking=True,
    )
    project_product_line_ids = fields.One2many(
        "project.product.line",
        "project_id",
        string="Project Products",
        copy=True,
    )
    project_approval_line_ids = fields.One2many(
        "project.approval.line",
        "project_id",
        string="Project Approvals",
        copy=False,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    project_total_cost = fields.Monetary(
        string="Project Total Cost",
        compute="_compute_project_financials",
        currency_field="currency_id",
        tracking=True,
    )
    utilized_amount = fields.Monetary(
        string="Utilized Amount",
        compute="_compute_project_financials",
        currency_field="currency_id",
        tracking=True,
    )
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_project_financials",
        currency_field="currency_id",
        tracking=True,
    )
    approval_request_count = fields.Integer(
        string="Purchase Requisitions",
        compute="_compute_approval_request_count",
    )
    can_approve_project = fields.Boolean(
        string="Can Approve Project",
        compute="_compute_can_approve_project",
    )

    @api.depends("project_approval_line_ids.status", "project_approval_line_ids.sequence")
    def _compute_current_approval_level_id(self):
        for project in self:
            pending = project.project_approval_line_ids.filtered(
                lambda line: line.status == "pending"
            ).sorted("sequence")
            project.current_approval_level_id = pending[:1].approval_level_id

    @api.depends(
        "project_product_line_ids.total_cost",
        "approval_state",
        "company_id",
    )
    def _compute_project_financials(self):
        Request = self.env["approval.request"].sudo()
        committed_states = Request._project_budget_committed_states()
        for project in self:
            total = sum(project.project_product_line_ids.mapped("total_cost"))
            if not project.id:
                project.project_total_cost = total
                project.utilized_amount = 0.0
                project.remaining_amount = total
                continue
            requests = Request.search(
                [
                    ("project_project_id", "=", project.id),
                    ("request_type", "=", "project_pr"),
                    ("request_status", "in", list(committed_states)),
                ]
            )
            utilized = sum(requests.mapped("amount"))
            project.project_total_cost = total
            project.utilized_amount = utilized
            project.remaining_amount = total - utilized

    def _compute_approval_request_count(self):
        Request = self.env["approval.request"].sudo()
        counts = Request.read_group(
            [("project_project_id", "in", self.ids), ("request_type", "=", "project_pr")],
            ["project_project_id"],
            ["project_project_id"],
        )
        mapped = {row["project_project_id"][0]: row["project_project_id_count"] for row in counts}
        for project in self:
            project.approval_request_count = mapped.get(project.id, 0)

    @api.depends_context("uid")
    @api.depends("approval_state", "project_approval_line_ids.status", "project_approval_line_ids.user_ids")
    def _compute_can_approve_project(self):
        user = self.env.user
        for project in self:
            line = project.project_approval_line_ids.filtered(lambda l: l.status == "pending")[:1]
            project.can_approve_project = bool(
                project.approval_state == "under_approval"
                and line
                and user in line.user_ids
            )

    def _prepare_project_approval_lines(self):
        self.ensure_one()
        if not self.approval_group_id:
            raise UserError(_("Please select an approval group before submitting the project."))
        levels = self.approval_group_id.level_ids.filtered(lambda level: level.active).sorted("sequence")
        if not levels:
            raise UserError(_("The selected approval group has no active approval levels."))
        commands = [(5, 0, 0)]
        for index, level in enumerate(levels):
            if not level.user_ids:
                raise UserError(_("Approval level '%s' has no approvers.") % level.display_name)
            commands.append(
                (
                    0,
                    0,
                    {
                        "approval_level_id": level.id,
                        "sequence": level.sequence,
                        "user_ids": [(6, 0, level.user_ids.ids)],
                        "status": "pending" if index == 0 else "waiting",
                    },
                )
            )
        return commands

    def action_submit_for_approval(self):
        for project in self:
            if project.approval_state != "draft":
                raise UserError(_("Only draft projects can be submitted for approval."))
            # if not project.project_product_line_ids:
            #     raise UserError(_("Please add at least one project product before submitting."))
            project.with_context(allow_project_approval_state_write=True).write(
                {
                    "project_approval_line_ids": project._prepare_project_approval_lines(),
                    "approval_state": "under_approval",
                }
            )
            project.sudo().message_post(body=_("Project submitted for approval by %s.") % self.env.user.display_name)

    def action_approve_project(self):
        for project in self:
            if project.approval_state != "under_approval":
                raise UserError(_("Only projects under approval can be approved."))
            line = project.project_approval_line_ids.filtered(lambda l: l.status == "pending")[:1]
            if not line:
                raise UserError(_("No pending approval level was found."))
            if self.env.user not in line.user_ids:
                raise UserError(_("You are not an approver for the current approval level."))
            line.sudo().write(
                {
                    "status": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_date": fields.Datetime.now(),
                }
            )
            project.sudo().message_post(
                body=_("Approval level '%s' approved by %s.")
                % (line.approval_level_id.display_name, self.env.user.display_name)
            )
            waiting = project.project_approval_line_ids.filtered(lambda l: l.status == "waiting").sorted("sequence")
            if waiting:
                waiting[:1].sudo().write({"status": "pending"})
            else:
                project.sudo().with_context(allow_project_approval_state_write=True).approval_state = "approved"
                project.sudo().message_post(body=_("Project approved."))

    def action_reject_project(self):
        for project in self:
            if project.approval_state != "under_approval":
                raise UserError(_("Only projects under approval can be rejected."))
            line = project.project_approval_line_ids.filtered(lambda l: l.status == "pending")[:1]
            if line and self.env.user not in line.user_ids and not self.env.user.has_group("project.group_project_manager"):
                raise UserError(_("You are not allowed to reject this project."))
            if line:
                line.sudo().write(
                    {
                        "status": "rejected",
                        "approved_by_id": self.env.user.id,
                        "approved_date": fields.Datetime.now(),
                    }
                )
            project.sudo().with_context(allow_project_approval_state_write=True).approval_state = "rejected"
            project.sudo().message_post(body=_("Project rejected by %s.") % self.env.user.display_name)

    def action_reset_project_to_draft(self):
        for project in self:
            if project.approval_state == "approved" and not self.env.user.has_group("project.group_project_manager"):
                raise UserError(_("Only Project Managers can reset an approved project."))
            project.with_context(allow_project_approval_state_write=True).write(
                {
                    "approval_state": "draft",
                    "project_approval_line_ids": [(5, 0, 0)],
                }
            )
            project.sudo().message_post(body=_("Project reset to draft by %s.") % self.env.user.display_name)

    def action_view_project_purchase_requisitions(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Purchase Requisitions"),
            "res_model": "approval.request",
            "view_mode": "list,form",
            "domain": [("project_project_id", "=", self.id), ("request_type", "=", "project_pr")],
            "context": {"default_project_project_id": self.id, "default_request_type": "project_pr"},
        }
        return action

    def write(self, vals):
        protected = {"approval_group_id", "project_product_line_ids"}
        if protected.intersection(vals):
            locked = self.filtered(lambda p: p.approval_state == "approved")
            if locked and not self.env.user.has_group("project.group_project_manager"):
                raise UserError(_("Only Project Managers can modify approved project budget information."))
        if "approval_state" in vals and not self.env.context.get("allow_project_approval_state_write"):
            allowed = {"draft", "under_approval", "approved", "rejected"}
            if vals["approval_state"] in allowed and not self.env.user.has_group("project.group_project_manager"):
                raise UserError(_("Use the project approval buttons to change the approval status."))
        return super().write(vals)
