# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'


    def _get_reconciled_info_JSON_values(self):
        self.ensure_one()
        reconciled_vals = []
        for partial, amount, counterpart_line in self._get_reconciled_invoices_partials():
            reconciled_vals.append(self._get_reconciled_vals(partial, amount, counterpart_line))
        return reconciled_vals
