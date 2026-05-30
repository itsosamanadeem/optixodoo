from odoo import models, fields, api #type: ignore

class ResPartner(models.Model):
    _inherit = "res.partner"
    # _rec_name = "code,name"
    code = fields.Char(string="Code", required=True, copy=False, readonly=True, index=True, default="Customer")
    cnic_number = fields.Char(string="CNIC Number")
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'Customer') == 'Customer':
                vals['code'] = self.env['ir.sequence'].next_by_code('res.partner.code') or 'Customer'
        return super(ResPartner, self).create(vals_list)
