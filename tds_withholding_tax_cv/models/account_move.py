# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_tds_amount(self, payment_id):
        if payment_id and payment_id.tds_tax_id:
            amt = self.amount_total * payment_id.tds_tax_id.amount / 100
            return float_round(amt - 0.001, 2, rounding_method='HALF-UP')
        return 0

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    for_wht = fields.Boolean('For WHT')


class AccountInvoiceTax(models.Model):
    _inherit = "account.tax"

    tds = fields.Boolean('WHT', default=False)

