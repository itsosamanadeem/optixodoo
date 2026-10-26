{
    'name': 'Cost Centre-wise Expenses',
    'version': '19.0.1.1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Cost centre and city expenses with prior-year comparison',
    'license': 'LGPL-3',
    'depends': ['account', 'analytic'],
    'external_dependencies': {'python': ['xlsxwriter']},
    'data': [
        'security/ir.model.access.csv',
        'report/expense_report.xml',
        'wizard/expense_report_views.xml',
    ],
    'installable': True,
}
