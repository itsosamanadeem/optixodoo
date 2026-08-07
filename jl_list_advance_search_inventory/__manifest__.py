# -*- coding: utf-8 -*-
#######################################################################################
#
#    OdooProvider
#
#    Copyright (C) OdooProvider(<https://www.odooprovider.cn>).
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
########################################################################################
{
    'name': 'List Advanced Filters in Inventory',
    'category': 'Tools',
    'version': '19.0.1.0.0',
    'sequence': 15,
    'summary': 'Advanced list search/filters for Inventory list views',
    'description': """This module extends Inventory list views with advanced search/filter inputs in the header row.
It enables fast, column-based filtering directly from the list view for stock-related records,
improving search speed and daily warehouse operations without leaving the current screen.""",
    'author': 'OdooProvider',
    'website': 'https://www.odooprovider.cn',
    'images': ['static/description/cover_image.png'],
    'depends': [
        # 'jl_list_advance_search',
        'stock',
    ],
    'assets': {
        'web.assets_backend': [
            "jl_list_advance_search_inventory/static/src/**/*",
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
}
