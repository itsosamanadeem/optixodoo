from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    fw_tax_category = fields.Selection([
        ('wht', 'Withholding Income Tax'), ('stsp', 'STSP / PRT Withholding'),
        ('sales', 'Sales Tax / FED in ST Mode'), ('extra', 'Extra Tax'),
        ('fed', 'FED Payable'), ('noncredit', 'Input Credit Not Allowed'),
    ], string='Accounting Report Tax Category',
        help='Classifies posted ledger amounts in the Optix payment and purchase annexure reports.')


class Partner(models.Model):
    _inherit = 'res.partner'

    fw_cnic = fields.Char('Report CNIC')
    fw_supplier_type = fields.Selection([
        ('registered', 'Registered'), ('unregistered', 'Unregistered'),
    ], string='Annexure Supplier Type')


class AccountMove(models.Model):
    _inherit = 'account.move'

    fw_challan_received = fields.Boolean('Tax Challan Received', copy=False)
    fw_hs_code = fields.Char('Annexure HS Code')
    fw_purchase_type = fields.Selection([
        ('goods', 'Goods'), ('service', 'Service'), ('electricity', 'Electricity'),
    ], string='Annexure Purchase Type')
    fw_prt_type = fields.Char('PRT Type')
    fw_deduction_doc_type = fields.Char('STSP / PRT Deduction Document Type')
    fw_deduction_date = fields.Date('STSP / PRT Deduction Date')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    fw_payment_nature = fields.Char('Payment Nature')
    fw_taxable_base = fields.Monetary('Taxable Amount (Company Currency)',
                                     currency_field='company_currency_id')
    fw_taxable_base_set = fields.Boolean('Use Specified Taxable Amount',
        help='Otherwise the report uses the gross payment as the taxable base.')
    fw_wht_rate = fields.Float('WHT Rate (%)', digits=(16, 6),
        help='Optional stated rate; otherwise the report shows the effective WHT / taxable amount rate.')
