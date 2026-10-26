from odoo import api, fields, models


class ApprovalProductLine(models.Model):
    _inherit = "approval.product.line"

    project_product_line_id = fields.Many2one(
        "project.product.line",
        string="Project Item",
        compute="_compute_project_product_line_id",
        store=True,
        readonly=True,
    )
    project_planned_qty = fields.Float(
        related="project_product_line_id.quantity",
        string="Project Planned Qty",
        readonly=True,
    )
    project_requested_qty = fields.Float(
        related="project_product_line_id.requested_qty",
        string="Project Requested Qty",
        readonly=True,
    )
    project_remaining_qty = fields.Float(
        related="project_product_line_id.remaining_qty",
        string="Project Remaining Qty",
        readonly=True,
    )
    project_estimated_unit_cost = fields.Monetary(
        related="project_product_line_id.unit_cost",
        string="Project Estimated Unit Cost",
        currency_field="currency_id",
        readonly=True,
    )

    @api.depends(
        "approval_request_id.request_type",
        "approval_request_id.project_project_id.project_product_line_ids.product_id",
        "product_id",
    )
    def _compute_project_product_line_id(self):
        for line in self:
            if not line.approval_request_id._is_project_pr():
                line.project_product_line_id = False
                continue
            project = line.approval_request_id.project_project_id
            line.project_product_line_id = project.project_product_line_ids.filtered(
                lambda project_line: project_line.product_id == line.product_id
            )[:1]

    @api.onchange("product_id")
    def _onchange_project_product_id(self):
        for line in self:
            if not line.approval_request_id._is_project_pr():
                continue
            project_line = line.approval_request_id.project_project_id.project_product_line_ids.filtered(
                lambda planned: planned.product_id == line.product_id
            )[:1]
            if project_line:
                line.product_uom_id = project_line.product_uom_id
                if not line.price_unit:
                    line.price_unit = project_line.unit_cost

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        requests = lines.mapped("approval_request_id").filtered(
            lambda request: not request._is_project_pr() or request.project_project_id
        )
        requests._project_budget_validate_all(include_commit_checks=False)
        return lines

    def write(self, vals):
        res = super().write(vals)
        if {"product_id", "quantity", "po_uom_qty", "price_unit", "status", "manager_refused"}.intersection(vals):
            requests = self.mapped("approval_request_id").filtered(
                lambda request: not request._is_project_pr() or request.project_project_id
            )
            requests._project_budget_validate_all(include_commit_checks=False)
        return res
