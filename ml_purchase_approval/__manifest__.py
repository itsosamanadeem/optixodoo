# -*- coding: utf-8 -*-
{
    "name": "Purchase Approval Flow",
    "version": "19.0.1.0.0",
    "category": "Purchases",
    "sequence": 225,
    "summary": "Multi-step purchase order approval with amount-based levels.",
    "website": "https://www.zalinotech.com",
    "author": "Zalino Tech (Private) Limited",
    "company": "Zalino Tech",
    "maintainer": "Zalino Tech",
    "support": "support@zalinotech.com",
    "description": """

Purchase Approval Flow adds a structured approval workflow to Odoo purchase orders.
Organizations can define approval groups, assign users to each level, configure amount
thresholds, and keep a complete history of recommendations, approvals, and returns.

Features
--------

* Create approval groups for different purchase policies
* Define multiple approval levels with minimum and maximum amounts
* Support recommendation and approval stages in the same flow
* Assign responsible users to each approval level
* Show action buttons only to authorized users
* Record comments, actions, and timestamps in approval history
* Return purchase orders for correction when needed
* Integrate directly with the standard Odoo purchase order workflow

    """,
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "wizard/approval_wizard.xml",
        "wizard/returned_wizard.xml",
        "views/approval_group_views.xml",
        "views/approval_level_views.xml",
        "views/purchase_order_views.xml",
    ],
    "demo": [],
    "images": [
        "static/description/assets/screenshots/2_screenshot.png",
        "static/description/assets/screenshots/1.png",
        "static/description/assets/screenshots/5.png",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": True,
}
