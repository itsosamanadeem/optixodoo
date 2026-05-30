# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    tds_threshold_check = fields.Boolean(string='Check TDS Threshold', default=False)
    wht_id = fields.Many2one('account.tax', copy=False)
    income_wht=fields.Boolean(string='Income Tax')
    income_tax_id=fields.Many2one('account.tax',string='Income Tax WHT')
    
class ResPartnerBank(models.Model):
    
    _inherit = 'res.partner.bank'
    
    branch_id = fields.Many2one('bank.branch', string="Branch")    
