# -*- coding: utf-8 -*-
{
    "name": "Project PR Budget Control",
    "version": "19.0.1.0.0",
    "category": "Project",
    "summary": "Project approval, planned products, and PR budget controls.",
    "author": "Zalino Tech",
    "website": "https://www.zalinotech.com",
    "depends": [
        "project",
        "approvals_purchase",
        "purchase_inherit",
        "ml_purchase_approval",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/project_project_views.xml",
        "views/approval_request_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
