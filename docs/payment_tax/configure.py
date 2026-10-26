"""Run in Odoo shell after module upgrade. Targets the audited Optix company only.
Does not commit: the caller chooses dry-run/rollback or commit.
"""
accounts = {567: ('wht', 'Tax withheld from payments to suppliers'),
            562: ('stsp', 'FBR sales tax withheld from suppliers'),
            563: ('stsp', 'SRB sales tax withheld from suppliers'),
            564: ('stsp', 'PRA sales tax withheld from suppliers'),
            565: ('stsp', 'KPK sales tax withheld from suppliers')}
for account_id, (category, expected_name) in accounts.items():
    account = env['account.account'].browse(account_id).exists()
    assert account and account.with_context(lang='en_US').name.lower() == expected_name.lower(), (account_id, expected_name)
    assert account.account_type == 'liability_current', account.display_name
    account.fw_tax_category = category
    taxes = env['account.tax'].with_context(active_test=False).search([('account_id', '=', account.id)])
    taxes.write({'payment_tax_category': category, 'is_income_tax': category == 'wht'})
    print('CLASSIFIED', account.id, category, taxes.ids)
for tax_id, expected_name, rate in [(172, 'IT Without Sales Tax Withheld 11%', 11), (177, 'IT Without Sales Tax Withheld 15%', 15)]:
    tax = env['account.tax'].browse(tax_id)
    assert tax.with_context(lang='en_US').name == expected_name and tax.amount_type == 'percent'
    assert tax.amount in (0, rate), 'Unexpected rate; review before replacing'
    tax.amount = rate
    print('CORRECTED RATE', tax.id, rate)
print('Payment tax configuration complete. Existing journal entries were not modified.')
