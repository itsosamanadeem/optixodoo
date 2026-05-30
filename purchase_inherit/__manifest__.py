# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Approval Chain',
    'version': '1.2',
    'category': 'Customizations',
    'sequence': -100,
    'summary': 'Purchase orders,Approval Chain',
    'website': 'https://www.odoo.com/app/purchase',
    'depends': ['purchase',
                'account_budget',
                'base',
                'web',
                'hr',
                'approvals',
                'approvals_purchase',
                'ml_purchase_approval',
                'account',
                'analytic',
                'product',
                'repair',
                'gatepass_slip',
    ],
    "data": [
        #security
        "security/groups.xml",
        "security/rules.xml",
        "security/ir.model.access.csv",

        #data
        "data/partner_sequence.xml",
        "data/product_sequence.xml",
        
        #views
        "views/warrenty.xml",
        "views/product_product.xml",
        "views/budget_analytic.xml",
        "views/hr_department.xml",
        "views/approval_product_line.xml",
        "views/approvals_menu_rename.xml",
        "views/purchase_order_line_views.xml",
        "views/purchase.xml",
        "views/repair_order.xml",
        "views/stock_picking.xml",
        "views/stock_move_line.xml",
        "views/res_partner.xml",
        "views/account_tax.xml",
        
        #wizards
        "wizard/budget_wizard.xml",
        "wizard/city_warning_wizard.xml",
        "wizard/stock_serial_import_wizard.xml",
        "wizard/account_payment_register_wizard.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_inherit/static/src/js/*',
            'purchase_inherit/static/src/scss/*',
            'purchase_inherit/static/src/xml/*',
        ],
    },
    'images': ['static/description/icon.svg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'author': 'Osama Nadeem',
    'license': 'LGPL-3',
}
