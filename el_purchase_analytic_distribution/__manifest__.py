# See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Analytic Distribution | PO Analytic Distribution | Purchase Distribution',
    'version': '19.0.1.0',
    'license': 'OPL-1',
    'author': 'ERP Labz',
    'maintainer': 'ERP Labz',
    'summary': 'This module allows you to define an analytic distribution at the Purchase order header level and automatically apply it to each newly created line \
    It also provides a one-click option to update all existing lines with the header’s analytic distribution. \
    Additionally, users can assign a specific purchase analytic account and propagate it to all order lines \
    All in One Analytic Distribution\
    Purchase Analytic Distribution\
    Purchase Analytic\
    Purchase distribution\
    PO distribution\
    Purchase Order analytic distribution\
    PO analytic distribution\
    Sale Analytic Distribution\
    Sale distribution\
    Sale Analytic\
    Invoice Analytic\
    Invoice Distribution\
    Analytic Distribution\
    Globel analytic distribution\
    Global analytic distribution\
    Invoice Analytic Distribution\
    Mass Analytic Distribution',
    'description': """
        Set Purchase Analytic Distribution on header for each Purchase lines Automatically
    """,
    'website': 'https://erplabz.com/',
    'category': 'Inventory/Purchase',
    'images': [],
    'depends': ['purchase','account',],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'price': 16,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
}
