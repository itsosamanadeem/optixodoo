# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Inherit Approval Chain',
    'version': '1.2',
    'category': 'Customizations',
    'sequence': -100,
    'summary': 'Purchase orders, tenders and agreements',
    'website': 'https://www.odoo.com/app/purchase',
    'depends': ['purchase',
    'base',
    'web',
    'hr',
    'approvals',
    'approvals_purchase',
    'ml_purchase_approval',
    'account',
    'analytic',
    ],
    "data": [
        "security/groups.xml",
        "security/rules.xml",
        
        "views/approval_product_line.xml",
        "views/purchase_order_line_views.xml",
        "views/purchase.xml",
        
        # "security/ir.model.access.csv"
    ],
    'assets': {
        # 'web.assets_backend': [
        #     'purchase_inherit/static/src/js/*',
        #     'purchase_inherit/static/src/scss/*',
        #     'purchase_inherit/static/src/xml/*',
        # ],
    },
    'images': ['static/description/icon.svg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'author': 'Osama Nadeem',
    'license': 'LGPL-3',
}
