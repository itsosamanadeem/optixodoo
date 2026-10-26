from odoo import api, fields, models


class ProjectProductLine(models.Model):
    _name = "project.product.line"
    _description = "Project Product Line"
    _order = "project_id, sequence, id"

    sequence = fields.Integer(default=10)
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="project_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="project_id.currency_id",
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        index=True,
    )
    description = fields.Char()
    quantity = fields.Float(string="Planned Qty", default=1.0, required=True)
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="UoM",
        required=True,
    )
    unit_cost = fields.Monetary(
        string="Estimated Unit Cost",
        currency_field="currency_id",
        required=True,
    )
    total_cost = fields.Monetary(
        string="Estimated Total",
        compute="_compute_total_cost",
        store=True,
        currency_field="currency_id",
    )
    requested_qty = fields.Float(
        string="Requested Qty",
        compute="_compute_requested_qty",
    )
    remaining_qty = fields.Float(
        string="Remaining Qty",
        compute="_compute_requested_qty",
    )

    _project_product_unique = models.Constraint(
        "UNIQUE(project_id, product_id)",
        "Each product can only be planned once per project.",
    )
    _project_product_quantity_positive = models.Constraint(
        "CHECK(quantity >= 0)",
        "Planned quantity cannot be negative.",
    )
    _project_product_unit_cost_positive = models.Constraint(
        "CHECK(unit_cost >= 0)",
        "Estimated unit cost cannot be negative.",
    )

    @api.depends("quantity", "unit_cost")
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.quantity * line.unit_cost

    @api.depends("project_id", "project_id.approval_request_count", "product_id", "quantity")
    def _compute_requested_qty(self):
        Request = self.env["approval.request"].sudo()
        committed_states = Request._project_budget_committed_states()
        for line in self:
            requested = 0.0
            if line.project_id and line.product_id:
                requests = Request.search(
                    [
                        ("project_project_id", "=", line.project_id.id),
                        ("request_type", "=", "project_pr"),
                        ("request_status", "in", list(committed_states)),
                    ]
                )
                pr_lines = requests.mapped("product_line_ids").filtered(
                    lambda pr_line: pr_line.product_id == line.product_id
                    and not pr_line.manager_refused
                    and pr_line.status != "refused"
                )
                requested = sum(pr_lines.mapped(lambda pr_line: pr_line.po_uom_qty or pr_line.quantity or 0.0))
            line.requested_qty = requested
            line.remaining_qty = line.quantity - requested

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            line.description = line.product_id.display_name
            line.product_uom_id = line.product_id.uom_id
            if not line.unit_cost:
                line.unit_cost = line.product_id.standard_price
