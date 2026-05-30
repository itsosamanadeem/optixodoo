from odoo import models, fields

class BankBranch(models.Model):
    _name = 'bank.branch'
    _description = 'Bank Branch'

    name = fields.Char(string="Branch Name", required=True)
