from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    request_type = fields.Selection(
        selection_add=[("project_pr", "Project PR")],
        ondelete={"project_pr": "set default"},
    )
    project_project_id = fields.Many2one(
        "project.project",
        string="Project",
        domain="[('approval_state', '=', 'approved'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    project_total_cost = fields.Monetary(
        related="project_project_id.project_total_cost",
        string="Project Total Cost",
        currency_field="currency_id",
        readonly=True,
    )
    project_utilized_amount = fields.Monetary(
        related="project_project_id.utilized_amount",
        string="Project Utilized Amount",
        currency_field="currency_id",
        readonly=True,
    )
    project_remaining_amount = fields.Monetary(
        related="project_project_id.remaining_amount",
        string="Project Remaining Amount",
        currency_field="currency_id",
        readonly=True,
    )
    allowed_project_product_ids = fields.Many2many(
        "product.product",
        string="Allowed Project Products",
        compute="_compute_allowed_project_product_ids",
    )

    def _is_project_pr(self):
        self.ensure_one()
        return self.request_type == "project_pr"

    @api.model
    def _project_budget_committed_states(self):
        return {
            "approved",
            "partial_approved",
            "purchase_order_created",
            "internal_transfer_created",
        }

    def _project_budget_currency_rounding(self):
        self.ensure_one()
        currency = (
            self.currency_id
            or self.company_id.currency_id
            or self.project_project_id.currency_id
            or self.env.company.currency_id
        )
        return currency.rounding if currency and currency.rounding > 0 else 0.01

    @api.depends("request_type", "project_project_id.project_product_line_ids.product_id")
    def _compute_allowed_project_product_ids(self):
        all_products = self.env["product.product"].search([])
        for request in self:
            if request._is_project_pr() and request.project_project_id:
                request.allowed_project_product_ids = request.project_project_id.project_product_line_ids.mapped("product_id")
            else:
                request.allowed_project_product_ids = all_products

    @api.onchange("project_project_id", "request_type")
    def _onchange_project_project_id(self):
        for request in self:
            if not request._is_project_pr():
                request.project_project_id = False
                continue
            if request.project_project_id:
                request.product_line_ids = [(5, 0, 0)]

    def _project_budget_line_amount(self, line):
        qty = line.po_uom_qty or line.quantity or 0.0
        return (line.price_unit or 0.0) * qty

    def _project_budget_active_lines(self):
        self.ensure_one()
        return self.product_line_ids.filtered(
            lambda line: line.product_id and not line.manager_refused and line.status != "refused"
        )

    def _project_budget_request_amount(self):
        self.ensure_one()
        return sum(self._project_budget_line_amount(line) for line in self._project_budget_active_lines())

    def _project_budget_validate_project(self):
        for request in self:
            if not request._is_project_pr():
                continue
            if not request.project_project_id:
                raise ValidationError(_("A Project PR must reference an approved Project."))
            project = request.project_project_id
            if project.approval_state != "approved":
                raise ValidationError(_("You can only create a Project PR for an approved project."))
            if request.company_id and project.company_id and request.company_id != project.company_id:
                raise ValidationError(_("The Project PR company must match the selected Project company."))

    def _project_budget_validate_products(self):
        for request in self:
            if not request._is_project_pr() or not request.project_project_id:
                continue
            project = request.project_project_id
            planned_by_product = {
                line.product_id.id: line
                for line in project.project_product_line_ids
                if line.product_id
            }
            for line in request._project_budget_active_lines():
                planned = planned_by_product.get(line.product_id.id)
                if not planned:
                    raise ValidationError(
                        _("Product '%(product)s' is not included in Project '%(project)s'.")
                        % {
                            "product": line.product_id.display_name,
                            "project": project.display_name,
                        }
                    )

    def _project_budget_existing_committed_amount(self):
        self.ensure_one()
        committed_states = self._project_budget_committed_states()
        requests = self.sudo().search(
            [
                ("project_project_id", "=", self.project_project_id.id),
                ("request_type", "=", "project_pr"),
                ("request_status", "in", list(committed_states)),
                ("id", "!=", self.id),
            ]
        )
        return sum(requests.mapped("amount"))

    def _project_budget_existing_product_qty(self, product):
        self.ensure_one()
        committed_states = self._project_budget_committed_states()
        requests = self.sudo().search(
            [
                ("project_project_id", "=", self.project_project_id.id),
                ("request_type", "=", "project_pr"),
                ("request_status", "in", list(committed_states)),
                ("id", "!=", self.id),
            ]
        )
        lines = requests.mapped("product_line_ids").filtered(
            lambda line: line.product_id == product and not line.manager_refused and line.status != "refused"
        )
        return sum(lines.mapped(lambda line: line.po_uom_qty or line.quantity or 0.0))

    def _project_budget_validate_quantity_and_amount(self):
        for request in self:
            if not request._is_project_pr() or not request.project_project_id:
                continue
            request.env.cr.execute(
                "SELECT id FROM project_project WHERE id = %s FOR UPDATE",
                [request.project_project_id.id],
            )
            request.project_project_id.invalidate_recordset(
                ["project_total_cost", "utilized_amount", "remaining_amount"]
            )
            planned_by_product = {
                line.product_id.id: line
                for line in request.project_project_id.project_product_line_ids
                if line.product_id
            }
            requested_by_product = {}
            for line in request._project_budget_active_lines():
                requested_by_product.setdefault(line.product_id, 0.0)
                requested_by_product[line.product_id] += line.po_uom_qty or line.quantity or 0.0
            for product, qty in requested_by_product.items():
                planned = planned_by_product.get(product.id)
                if not planned:
                    continue
                already_requested = request._project_budget_existing_product_qty(product)
                remaining_qty = planned.quantity - already_requested
                if float_compare(qty, remaining_qty, precision_rounding=planned.product_uom_id.rounding) > 0:
                    raise ValidationError(
                        _("Only %(qty)s units of %(product)s remain available for this project.")
                        % {
                            "qty": remaining_qty,
                            "product": product.display_name,
                        }
                    )
            requested_amount = request._project_budget_request_amount()
            utilized = request._project_budget_existing_committed_amount()
            remaining = request.project_project_id.project_total_cost - utilized
            precision = request._project_budget_currency_rounding()
            if float_compare(requested_amount, remaining, precision_rounding=precision) > 0:
                raise ValidationError(
                    _(
                        "The Project PR exceeds the remaining budget of the project.\n\n"
                        "Project Budget: %(budget)s\n"
                        "Utilized Amount: %(utilized)s\n"
                        "Remaining Amount: %(remaining)s\n"
                        "Requested Amount: %(requested)s"
                    )
                    % {
                        "budget": request.project_project_id.project_total_cost,
                        "utilized": utilized,
                        "remaining": remaining,
                        "requested": requested_amount,
                    }
                )

    def _project_budget_validate_all(self, include_commit_checks=False):
        self._project_budget_validate_project()
        self._project_budget_validate_products()
        if include_commit_checks:
            self._project_budget_validate_quantity_and_amount()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("request_type", "pr") != "project_pr":
                vals["project_project_id"] = False
        records = super().create(vals_list)
        records._project_budget_validate_all(include_commit_checks=False)
        return records

    def write(self, vals):
        if vals.get("request_type") and vals["request_type"] != "project_pr":
            vals = dict(vals, project_project_id=False)
        res = super().write(vals)
        if {"project_project_id", "product_line_ids", "request_type", "company_id"}.intersection(vals):
            self._project_budget_validate_all(include_commit_checks=False)
        return res

    def action_confirm(self):
        self._project_budget_validate_all(include_commit_checks=True)
        return super().action_confirm()

    def action_approve(self, approver=None):
        self._project_budget_validate_all(include_commit_checks=True)
        return super().action_approve(approver=approver)

    def action_create_purchase_orders(self):
        self._project_budget_validate_all(include_commit_checks=True)
        return super().action_create_purchase_orders()

    def create_internal_transfers_for_request(self):
        self._project_budget_validate_all(include_commit_checks=True)
        return super().create_internal_transfers_for_request()
