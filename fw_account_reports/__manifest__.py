{
    'name': 'Optix Accounting Reports',
    'version': '19.0.1.0.0',
    'author': 'Optix',
    'category': 'Accounting/Accounting',
    'summary': 'Supplier aging, income, payments, purchase tax annexure and transactions',
    'license': 'LGPL-3',
    'depends': ['account', 'analytic'],
    'data': ['security/ir.model.access.csv', 'views/report_fields.xml',
             'report/report.xml', 'wizard/report_views.xml'],
    'installable': True,
}
