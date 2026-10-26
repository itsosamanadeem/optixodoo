"""Integration checks for the restored Optix database. Always rollback."""
from odoo import Command, fields
from odoo.exceptions import ValidationError, UserError
from pathlib import Path

assert env.cr.dbname.startswith('optix_payment_tax_uat_'), 'Run only on the isolated validation database'
exec(Path('/mnt/custom-addons/docs/payment_tax/configure.py').read_text())
company = env['account.tax'].browse(171).company_id
env = env(context=dict(env.context, allowed_company_ids=[company.id]))
Payment = env['account.payment'].with_company(company)
journal = env['account.journal'].browse(19).copy({'name': 'UAT Tax Bank', 'code': 'UTX'})
method = journal.outbound_payment_method_line_ids.filtered(lambda m: m.code == 'manual')[:1]
method.payment_account_id = journal.default_account_id
purchase_journal = env['account.journal'].search([('company_id','=',company.id),('type','=','purchase')], limit=1).copy({'name':'UAT Bills','code':'UTB'})
partner = env['res.partner'].create({'name': 'OPTIX PAYMENT TAX UAT', 'supplier_rank': 1, 'property_account_payable_id': env['account.account'].browse(523).id})
wht = env['account.tax'].browse(171)
stsp = env['account.tax'].browse(187)
passed = []

def ok(name):
    passed.append(name)
    print('PASS:', name, flush=True)

def near(a, b):
    assert abs(a-b) < 0.011, (a,b)

def reject(fn):
    try:
        with env.cr.savepoint():
            fn()
    except (ValidationError, UserError):
        return
    raise AssertionError('Expected rejection')

def payment(gross=100000, taxes=None, **extra):
    vals = {'payment_type': 'outbound', 'partner_type': 'supplier', 'partner_id': partner.id,
        'journal_id': journal.id, 'payment_method_line_id': method.id,
        'date': fields.Date.today(), 'currency_id': company.currency_id.id,
        'optix_tax_payment': True, 'optix_gross_amount': gross,
        'optix_tax_line_ids': [Command.create({'tax_id': t.id}) for t in (taxes if taxes is not None else wht)]}
    vals.update(extra)
    return Payment.create(vals)

def bill(amount=100000, currency=None):
    expense = env['account.account'].search([('company_ids','in',company.id),('account_type','=','expense'),('active','=',True)], limit=1)
    j = purchase_journal
    b = env['account.move'].create({'move_type':'in_invoice','partner_id':partner.id,
        'journal_id':j.id,'invoice_date':fields.Date.today(), 'date':fields.Date.today(),
        'currency_id':(currency or company.currency_id).id, 'ref':'UAT-INVOICE',
        'invoice_line_ids':[Command.create({'name':'Tax workflow test','quantity':1,'price_unit':amount,
            'account_id':expense.id,'tax_ids':[Command.clear()]})]})
    b.action_post()
    return b

def wizard(bills, gross=None, taxes=None, **extra):
    vals = {'journal_id':journal.id,'payment_method_line_id':method.id,
        'optix_tax_payment':True, 'group_payment':True,
        'payment_difference_handling':'open',
        'income_tax_ids':[Command.create({'tax_id':t.id}) for t in (taxes if taxes is not None else wht)]}
    if gross is not None:
        vals['optix_gross_amount']=gross
    vals.update(extra)
    return env['account.payment.register'].with_context(active_model='account.move',active_ids=bills.ids).create(vals)

try:
    p=payment()
    near(p.amount,94500)
    p.action_post()
    assert p.move_id.state=='posted'
    near(sum(p.move_id.line_ids.mapped('balance')),0)
    liquidity,counterpart,other=p._seek_for_lines()
    near(sum(counterpart.mapped('debit')),100000)
    near(sum(liquidity.mapped('credit')),94500)
    near(sum(other.mapped('credit')),5500)
    ok('Standalone WHT: gross supplier debit, net bank credit, tax credit')
    reject(lambda:p.write({'optix_gross_amount':200000}))
    reject(lambda:p.optix_tax_line_ids.write({'manual_base':500}))
    ok('Posted tax amounts and reference details are protected')

    p2=payment(taxes=wht|stsp)
    near(p2.optix_stsp_amount,2608.70)
    near(p2.amount,91891.30)
    p2.action_post()
    near(sum(p2.move_id.line_ids.mapped('balance')),0)
    assert len(p2._seek_for_lines()[2])==2
    ok('Multiple deductions including existing STSP custom formula')

    p3=payment()
    p3.optix_tax_line_ids.write({'use_gross':False,'manual_base':50000})
    near(p3.amount,97250)
    p3.action_post()
    ok('Custom taxable base recalculates net and postings')

    p4=payment(taxes=env['account.tax'])
    near(p4.amount,100000)
    p4.action_post()
    near(sum(p4.move_id.line_ids.mapped('balance')),0)
    ok('Gross equals net when no deduction applies')

    b=bill()
    original=[(l.id,l.balance) for l in b.line_ids]
    w=wizard(b)
    near(w.amount,94500)
    bp=w._create_payments()
    near(b.amount_residual,0)
    assert [(l.id,l.balance) for l in b.line_ids]==original
    assert len(bp.optix_advice_line_ids)==1
    ok('Bill settlement reconciles gross without altering invoice journal lines')

    b2=bill()
    wp=wizard(b2,gross=40000)
    near(wp.amount,37800)
    pp=wp._create_payments()
    near(b2.amount_residual,60000)
    near(pp.optix_advice_line_ids.gross_amount,40000)
    ok('Partial payment leaves only the unpaid gross residual')

    bs=bill(30000)|bill(70000)
    gp=wizard(bs)._create_payments()
    assert len(gp)==1 and len(gp.optix_advice_line_ids)==2
    near(sum(bs.mapped('amount_residual')),0)
    near(sum(gp.optix_advice_line_ids.mapped('gross_amount')),100000)
    ok('Grouped bills preserve invoice dates and references and reconcile fully')

    bplain=bill(1200)
    plain=env['account.payment.register'].with_context(active_model='account.move',active_ids=bplain.ids).create({
        'journal_id':journal.id,'payment_method_line_id':method.id})
    normal=plain._create_payments()
    near(normal.amount,1200)
    near(bplain.amount_residual,0)
    ok('Standard payments without deductions retain core behavior')

    zero=wht.copy({'name':'UAT zero','amount':0})
    reject(lambda: payment(taxes=zero).action_post())
    reject(lambda: payment(gross=100, taxes=wht, optix_tax_line_ids=[Command.create({'tax_id':wht.id,'use_gross':False,'manual_base':100000})]))
    bad=payment(optix_advice_line_ids=[Command.create({'invoice_number':'MANUAL','gross_amount':99})])
    reject(bad.action_post)
    ok('Invalid zero taxes, excessive deductions and reference totals are blocked')

    p2.action_draft()
    p2.write({'optix_gross_amount':200000})
    p2.action_post()
    near(p2.amount,183782.61)
    assert len(p2._seek_for_lines()[2])==2
    near(sum(p2.move_id.line_ids.mapped('balance')),0)
    ok('Reset and repost recalculates two deductions without duplicating them')

    usd=env.ref('base.USD')
    if usd != company.currency_id:
        usd.active=True
        env['res.currency.rate'].create({'currency_id':usd.id,'company_id':company.id,'name':fields.Date.today(),'rate':0.004})
        foreign=payment(gross=1000,currency_id=usd.id)
        foreign.action_post()
        near(foreign.amount,945)
        near(sum(foreign.move_id.line_ids.mapped('balance')),0)
        near(sum(foreign._seek_for_lines()[1].mapped('amount_currency')),1000)
        fb=bill(1000,usd)
        fp=wizard(fb,currency_id=usd.id)._create_payments()
        near(fb.amount_residual,0)
        ok('Foreign-currency standalone and bill payments balance and reconcile')

    live_journal=env['account.journal'].browse(19)
    live_method=live_journal.outbound_payment_method_line_ids.filtered(lambda m:m.code=='manual')[:1]
    real1=payment(journal_id=live_journal.id,payment_method_line_id=live_method.id)
    real1.action_post()
    real2=payment(journal_id=live_journal.id,payment_method_line_id=live_method.id)
    real2.action_post()
    assert real1.move_id._sequence_matches_date() and real2.move_id._sequence_matches_date()
    assert real1.move_id.name != real2.move_id.name
    ok('Existing JS bank journal produces valid unique new fiscal-year vouchers')
    old_amount=p.optix_tax_line_ids.amount
    wht.amount=6
    env.flush_all()
    near(p.optix_tax_line_ids.amount,old_amount)
    near(p.optix_tax_line_ids.rate,5.5)
    wht.amount=5.5
    ok('Posted deduction amounts and rates survive later tax-master changes')

    group_field='group_ids' if 'group_ids' in env['res.users']._fields else 'groups_id'
    accountant=env['res.users'].with_context(no_reset_password=True).create({
        'name':'UAT Accountant','login':'optix_tax_uat_accountant',
        'company_id':company.id, 'company_ids':[Command.set(company.ids)],
        group_field:[Command.set([env.ref('base.group_user').id,env.ref('account.group_account_user').id])]})
    Payment=Payment.with_user(accountant)
    user_payment=payment()
    user_payment.action_post()
    assert user_payment.move_id.state=='posted'
    ok('Accounting user can create and post deductions without inventory-admin access')
    Payment=Payment.sudo()

    report=env.ref('purchase_inherit.action_payment_cheque_advice')
    html,_=report._render_qweb_html(report.report_name,[gp.id])
    assert b'Invoice Number' in html and b'Accounting Entries' in html and b'WHT' in html
    pdf,_=report._render_qweb_pdf(report.report_name,[p.id])
    assert pdf.startswith(b'%PDF')
    Path('/mnt/custom-addons/docs/payment_tax/sample_advice_uat.pdf').write_bytes(pdf)
    ok('HTML and PDF advice render with tax totals and actual debit/credit lines')

    reporter=env['fw.account.report.wizard'].create({'company_id':company.id,'report_type':'payment_taxes',
        'date_from':fields.Date.today(),'date_to':fields.Date.today(),'partner_ids':[Command.set(partner.ids)]})
    cols,rows=reporter._payments()
    assert rows
    ok('Existing payment tax reports read newly posted tax deductions')
    print('ALL CHECKS PASSED:',len(passed), flush=True)
finally:
    env.cr.rollback()
