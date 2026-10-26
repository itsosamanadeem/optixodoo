import base64

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountingReports(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Report Test Company', 'currency_id': cls.env.company.currency_id.id,
            'country_id': cls.env.ref('base.pk').id, 'account_fiscal_country_id': cls.env.ref('base.pk').id})
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))
        cls.partner = cls.env['res.partner'].create({'name': '=Supplier <Test>', 'ref': 'V001', 'supplier_rank': 1})
        specs = [('PAY', 'liability_payable'), ('EXP', 'expense'), ('INC', 'income'),
                 ('BNK', 'asset_cash'), ('WHT', 'liability_current'), ('STSP', 'liability_current')]
        cls.accounts = {}
        for code, kind in specs:
            cls.accounts[code] = cls.env['account.account'].create({
                'name': code, 'code': 'FWT' + code, 'account_type': kind,
                'company_ids': [Command.set(cls.company.ids)], 'reconcile': code in ('PAY', 'BNK'),
                'fw_tax_category': code.lower() if code in ('WHT', 'STSP') else False})
        cls.partner.with_company(cls.company).property_account_payable_id = cls.accounts['PAY']
        cls.journal = cls.env['account.journal'].create({
            'name': 'Report General', 'code': 'FWT', 'type': 'general', 'company_id': cls.company.id})
        cls.bank = cls.env['account.journal'].create({
            'name': 'Report Bank', 'code': 'FWB', 'type': 'bank', 'company_id': cls.company.id,
            'default_account_id': cls.accounts['BNK'].id})
        cls.bank.outbound_payment_method_line_ids.payment_account_id = cls.accounts['BNK']
        cls.plan = cls.env['account.analytic.plan'].create({'name': 'Test Cost'})
        cls.cost_a, cls.cost_b = cls.env['account.analytic.account'].create([
            {'name': 'A', 'code': '001', 'plan_id': cls.plan.id},
            {'name': 'B', 'code': '002', 'plan_id': cls.plan.id}])

    def wizard(self, kind, **values):
        return self.env['fw.account.report.wizard'].create(dict(
            company_id=self.company.id, report_type=kind, date_from='2026-04-01', date_to='2026-04-30',
            cost_plan_id=self.plan.id, city_plan_id=False, **values))

    def entry(self, date, amounts, post=True, journal=None, distribution=None):
        move = self.env['account.move'].create({
            'date': date, 'journal_id': (journal or self.journal).id,
            'line_ids': [Command.create({
                'name': 'Test ' + code, 'account_id': self.accounts[code].id,
                'partner_id': self.partner.id, 'debit': max(amount, 0), 'credit': max(-amount, 0),
                'date_maturity': date if code == 'PAY' else False,
                'analytic_distribution': distribution if code == 'INC' else False,
            }) for code, amount in amounts]})
        if post:
            move.action_post()
        return move

    def detail(self, wizard):
        return [r['cells'] for r in wizard._report_data()['rows'] if r['kind'] == 'line']

    def test_historical_aging_and_supplier_balances(self):
        bill = self.entry('2026-03-31', [('EXP', 1000), ('PAY', -1000)])
        early = self.entry('2026-04-15', [('PAY', 200), ('BNK', -200)])
        late = self.entry('2026-05-05', [('PAY', 800), ('BNK', -800)])
        payable = (bill + early + late).line_ids.filtered(lambda l: l.account_id == self.accounts['PAY'])
        payable.reconcile()
        self.assertTrue(all(payable.mapped('reconciled')))
        aging = self.wizard('aging')
        rows = self.detail(aging)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][-1], 800)
        self.assertEqual(rows[0][14], 800)  # exactly 30 days overdue
        suppliers = self.detail(self.wizard('suppliers'))
        self.assertEqual(suppliers[0][2:], [-1000, 200, 0, -800])
        aging.date_to = '2026-05-31'
        self.assertFalse(self.detail(aging))

    def test_aging_bucket_boundaries_and_unadjusted_advance(self):
        from datetime import date, timedelta
        dates = [-1, 0, 1, 30, 31, 60, 61, 90, 91, 120, 121, 150, 151]
        for days in dates:
            move = self.entry('2026-01-01', [('EXP', 10), ('PAY', -10)])
            move.line_ids.filtered(lambda l: l.account_id == self.accounts['PAY']).date_maturity = date(2026, 4, 30) - timedelta(days=days)
        self.entry('2026-04-01', [('PAY', 5), ('BNK', -5)])
        data = self.wizard('aging')._report_data()
        self.assertEqual(data['rows'][-1]['cells'][12:20], [10, 10, 20, 20, 20, 20, 20, 10])
        self.assertEqual(data['rows'][-1]['cells'][-1], 125)

    def test_income_allocation_prior_year_and_drafts(self):
        split = {str(self.cost_a.id): 60, str(self.cost_b.id): 40}
        self.entry('2026-04-05', [('INC', -1000), ('BNK', 1000)], distribution=split)
        self.entry('2026-04-06', [('INC', 100), ('BNK', -100)], distribution=split)
        self.entry('2025-04-05', [('INC', -200), ('BNK', 200)], distribution=split)
        self.entry('2026-04-07', [('INC', -999), ('BNK', 999)], post=False, distribution=split)
        wizard = self.wizard('income')
        self.assertEqual(wizard._report_data()['rows'][-1]['cells'][2:], [-900, -200])
        wizard.cost_center_ids = self.cost_a
        self.assertEqual(wizard._report_data()['rows'][-1]['cells'][2:], [-540, -120])

    def test_payment_deductions_and_cutoff(self):
        move = self.entry('2026-04-10', [('PAY', 1000), ('BNK', -850), ('WHT', -100), ('STSP', -50)], journal=self.bank)
        payment = self.env['account.payment'].create({
            'company_id': self.company.id, 'journal_id': self.bank.id, 'partner_id': self.partner.id,
            'payment_type': 'outbound', 'partner_type': 'supplier', 'date': '2026-04-10',
            'amount': 850, 'move_id': move.id, 'state': 'paid',
            'fw_taxable_base_set': True, 'fw_taxable_base': 800})
        bill = self.entry('2026-05-01', [('EXP', 1000), ('PAY', -1000)])
        (bill + move).line_ids.filtered(lambda l: l.account_id == self.accounts['PAY']).reconcile()
        row = self.detail(self.wizard('payments'))[0]
        self.assertEqual(row[6:], [1000, 100, 50, 850, 0, 0, 1000])
        tax_row = self.detail(self.wizard('payment_taxes'))[0]
        self.assertEqual(tax_row[4:11], [1000, 800, 12.5, 100, 50, 850, 850])
        self.assertEqual(payment.move_id, move)

    def test_annexure_bill_refund_and_metadata(self):
        tax_account = self.env['account.account'].create({
            'name': 'Input tax', 'code': 'FWTST', 'account_type': 'asset_current',
            'company_ids': [Command.set(self.company.ids)], 'fw_tax_category': 'sales'})
        group = self.env['account.tax.group'].create({'name': 'Report Tax', 'company_id': self.company.id})
        tax = self.env['account.tax'].create({
            'name': '15%', 'amount': 15, 'amount_type': 'percent', 'type_tax_use': 'purchase',
            'company_id': self.company.id, 'tax_group_id': group.id,
            'invoice_repartition_line_ids': [Command.create({'repartition_type': 'base'}), Command.create({'repartition_type': 'tax', 'account_id': tax_account.id})],
            'refund_repartition_line_ids': [Command.create({'repartition_type': 'base'}), Command.create({'repartition_type': 'tax', 'account_id': tax_account.id})]})
        journal = self.env['account.journal'].create({'name': 'Purchases', 'code': 'FWP', 'type': 'purchase', 'company_id': self.company.id})
        for kind, amount in [('in_invoice', 1000), ('in_refund', 200)]:
            move = self.env['account.move'].create({
                'move_type': kind, 'journal_id': journal.id, 'partner_id': self.partner.id,
                'date': '2026-04-11', 'invoice_date': '2026-04-11', 'fw_hs_code': '1234',
                'invoice_line_ids': [Command.create({'name': 'Service', 'account_id': self.accounts['EXP'].id,
                    'quantity': 1, 'price_unit': amount, 'tax_ids': [Command.set(tax.ids)]})]})
            move.action_post()
        data = self.wizard('annexure')._report_data()
        self.assertEqual(data['rows'][-1]['cells'][14:16], [800, 120])
        self.assertEqual(data['rows'][0]['cells'][9], '1234')

    def test_transactions_preview_csv_and_company_guard(self):
        self.entry('2026-04-10', [('EXP', 100), ('PAY', -100)])
        self.entry('2026-04-11', [('EXP', 20), ('PAY', -20)], post=False)
        wizard = self.wizard('transactions')
        self.assertEqual(wizard._report_data()['rows'][-1]['cells'][5:7], [100, 100])
        wizard.target_moves = 'all'
        self.assertEqual(wizard._report_data()['rows'][-1]['cells'][5:7], [120, 120])
        for kind in ['aging', 'income', 'payments', 'payment_taxes', 'annexure', 'suppliers', 'transactions']:
            report = self.wizard(kind)
            report.action_preview()
            self.assertIn('Report Test Company', report.preview)
            self.assertEqual(report.action_print()['report_type'], 'qweb-pdf')
            report.action_export()
            self.assertTrue(base64.b64decode(report.export_file).startswith(b'\xef\xbb\xbf'))
        supplier = self.wizard('suppliers')
        supplier.action_export()
        self.assertIn("'=Supplier <Test>", base64.b64decode(supplier.export_file).decode('utf-8-sig'))
        other_company = self.env['res.company'].create({'name': 'Inaccessible'})
        wizard.company_id = other_company
        with self.assertRaises(AccessError):
            wizard._report_data()
        wizard.company_id = self.company
        wizard.date_to = '2026-03-01'
        with self.assertRaises(ValidationError):
            wizard._report_data()
