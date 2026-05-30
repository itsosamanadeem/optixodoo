# from odoo import fields, models, api , _ # type: ignore
# from odoo.exceptions import UserError # type: ignore

# class VendorPaymentTaxLine(models.Model):
#     _name = "account.payment.register.tax.line"
#     _description = "Payment Register Income Tax Line"

#     payment_id = fields.Many2one(
#         "account.payment",
#         string="Payment Register",
#         required=True,
#         ondelete="cascade",
#     )
#     tax_id = fields.Many2one("account.tax", string="Tax", required=True)
#     amount = fields.Float(string="Amount", compute="_compute_amount")
#     income_tax_account_id = fields.Many2one(
#         "account.account",
#         string="Income Tax Account",
#         required=True,
#     )
    
#     @api.depends("tax_id", "payment_id.amount_before_tax", "payment_id.currency_id", "payment_id.partner_id")
#     def _compute_amount(self):
#         for line in self:
#             if not line.tax_id or not line.payment_id:
#                 line.amount = 0.0
#                 continue

#             line.amount = line.payment_id._get_tax_amount_for_tax(line.tax_id)

# class VendorPaymentTax(models.Model):
#     _inherit = "account.payment"

#     amount_before_tax = fields.Monetary(
#         string="Base Amount",
#         currency_field="currency_id",
#         copy=False,
#     )
#     income_tax_ids = fields.One2many(
#         "account.payment.register.tax.line",
#         "payment_id",
#         string="Income Tax Line",
#     )

#     def _get_tax_amount_for_tax(self, tax):
#         self.ensure_one()
#         if not tax:
#             return 0.0

#         base_amount = self.amount_before_tax or self.amount or 0.0
#         tax_data = tax.compute_all(
#             base_amount,
#             currency=self.currency_id,
#             quantity=1.0,
#             partner=self.partner_id,
#         )
#         return tax_data["total_included"] - tax_data["total_excluded"]

#     def _get_total_income_tax_amount(self):
#         self.ensure_one()
#         return sum(self.income_tax_ids.mapped("amount"))

#     def _recompute_amount_from_income_tax(self):
#         for payment in self:
#             base_amount = payment.amount_before_tax or payment.amount or 0.0
#             total_tax = 0.0
#             for tax_line in payment.income_tax_ids:
#                 if not tax_line.tax_id:
#                     continue
#                 total_tax += payment._get_tax_amount_for_tax(tax_line.tax_id)

#             new_amount = base_amount + total_tax
#             if payment.amount != new_amount:
#                 payment.with_context(skip_income_tax_amount_sync=True).write({"amount": new_amount})

#     @api.onchange("amount")
#     def _onchange_set_amount_before_tax(self):
#         if self._context.get("skip_income_tax_amount_sync"):
#             return
#         for payment in self:
#             payment.amount_before_tax = payment.amount or 0.0

#     @api.onchange("income_tax_ids", "income_tax_ids.tax_id", "amount_before_tax", "currency_id", "partner_id")
#     def _onchange_income_tax_ids_update_amount(self):
#         for payment in self:
#             if payment._context.get("skip_income_tax_amount_sync"):
#                 continue

#             base_amount = payment.amount_before_tax or payment.amount or 0.0
#             total_tax = 0.0
#             for tax_line in payment.income_tax_ids:
#                 if not tax_line.tax_id:
#                     tax_line.amount = 0.0
#                     continue
#                 tax_line.amount = payment._get_tax_amount_for_tax(tax_line.tax_id)
#                 total_tax += tax_line.amount
#             payment.with_context(skip_income_tax_amount_sync=True).amount = base_amount + total_tax

#     @api.model_create_multi
#     def create(self, vals_list):
#         records = super().create(vals_list)
#         records._recompute_amount_from_income_tax()
#         return records

#     def write(self, vals):
#         res = super().write(vals)
#         if self._context.get("skip_income_tax_amount_sync"):
#             return res

#         tracked_fields = {"income_tax_ids", "amount_before_tax", "currency_id", "partner_id"}
#         if tracked_fields.intersection(vals.keys()):
#             self._recompute_amount_from_income_tax()
#         return res

#     def action_post(self):
#         res = super().action_post()
#         # for payment in self:
#         #     move = payment.move_id
#         #     if not move:
#         #         raise UserError(_("No journal entry found for this payment. Please ensure the payment is properly posted."))
#         #     #     continue

#             # for tax_line in payment.income_tax_ids:
#                 # if not tax_line.amount or not tax_line.income_tax_account_id:
#                 #     continue

#                 # exists = self.env["account.move.line"].search_count(
#                 #     [("move_id", "=", move.id), ("related_amount_id", "=", tax_line.id)]
#                 # )
#                 # if exists:
#                 #     continue

#                 # self.env["account.move.line"].with_context(check_move_validity=False).create({
#                 #     'move_id': payment.move_id.id,
#                 #     "name": _("Income Tax for %s") % (tax_line.tax_id.name or ""),
#                 #     "account_id": tax_line.income_tax_account_id.id,
#                 #     "partner_id": payment.partner_id.id,
#                 #     "debit": 0.0,
#                 #     "credit": abs(tax_line.amount),
#                 #     "related_amount_id": tax_line.id,
#                 # })

#         return res
    
# class AccountMoveLine(models.Model):
#     _inherit = "account.move.line"

#     related_amount_id = fields.Many2one("account.payment.register.tax.line", string="Related Payment", copy=False)
