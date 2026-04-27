# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Gate Pass (In/Out)',
    'description':'Gate Pass Functionality of IN and OUT',
    'author': 'Osama Nadeem',
    'version': '1.2',
    'live_test_url':'https://www.youtube.com/watch?v=qfgFQGLNR0k',
    'sequence':-1000,
    'price': 40.00,

    'depends':['base','stock'],
    'data':['views/menu.xml',
            'views/gate_pass_view.xml',
            'views/stock_picking.xml',
            'views/gate_pass_report.xml',
            'views/gate_pass_sequence.xml',
            'security/ir.model.access.csv'],
    'installable':True,
    'application':True,
    'auto_install':False,
    'license':'LGPL-3',
    'images':['static/description/logo.jpeg']

}
