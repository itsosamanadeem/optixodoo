# -*- coding: utf-8 -*-
{
    'name': 'TDS or Withholding Tax CV',
    'version': '1.2',
    'category': 'Accounting & Finance',
    'sequence': 1,
    'summary': 'Tax Deducted at Source(TDS) or Withholding Tax.',
    'description': """
Manage Tax Deducted at Source(TDS) or Withholding Tax
===========================================================

This application allows you to apply TDS or withholding tax at the time of invoice or payment.

    """,
    'website': 'http://www.technaureus.com/',
    'author': 'Technaureus Info Solutions Pvt. Ltd.',
    'depends': ['account'],
    'price': 165,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'data': [
        'security/ir.model.access.csv',
        'views/account_view.xml',
        'views/res_partner_view.xml',
        'views/account_payment_view.xml',
        # 'views/account_invoice_view.xml',
        # 'report/report_invoice.xml',
        'views/bank_branch.xml',
    ],
    'demo': [],
    'css': [],
    'images': ['images/tds_screenshot.png', 'dxl_multi_payment_reconciliation'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url': 'https://www.youtube.com/watch?v=_KfswiLoSok'
}
