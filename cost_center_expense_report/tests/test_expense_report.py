from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCostCenterExpenses(TransactionCase):
    def _assert_excel_totals(self, wizard, actual, previous):
        action = wizard.action_export_excel()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertIn('field=excel_file', action['url'])
        self.assertTrue(wizard.excel_filename.endswith('.xlsx'))
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        with ZipFile(io.BytesIO(base64.b64decode(wizard.excel_file))) as archive:
            self.assertIsNone(archive.testzip())
            sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
            self.assertFalse(sheet.findall('.//s:f', ns))
            cells = sheet.findall('s:sheetData/s:row', ns)[-1].findall('s:c', ns)
            numbers = {cell.attrib['r'][0]: float(cell.find('s:v', ns).text)
                       for cell in cells if cell.attrib.get('t') != 's' and cell.find('s:v', ns) is not None}
            self.assertEqual(numbers['C'], actual)
            self.assertEqual(numbers['D'], previous)
            return archive.read('xl/sharedStrings.xml').decode()

    def test_allocations_comparison_and_rendering(self):
        company = self.env['res.company'].create({
            'name': 'Cost Centre Report Test', 'currency_id': self.env.company.currency_id.id,
        })
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=company.ids))
        cost_plan = self.env['account.analytic.plan'].create({'name': 'Report test cost'})
        city_plan = self.env['account.analytic.plan'].create({'name': 'Report test city'})
        accounts = self.env['account.analytic.account'].create([
            {'name': 'Sales', 'code': '110', 'plan_id': cost_plan.id},
            {'name': 'Finance', 'code': '970', 'plan_id': cost_plan.id},
            {'name': 'Karachi', 'code': '211', 'plan_id': city_plan.id},
        ])
        expense, offset = self.env['account.account'].create([
            {'name': 'Report Expense', 'code': 'CCEXPTEST', 'account_type': 'expense',
             'company_ids': [Command.set(company.ids)]},
            {'name': 'Report Offset', 'code': 'CCOFFTEST', 'account_type': 'asset_current',
             'company_ids': [Command.set(company.ids)]},
        ])
        journal = self.env['account.journal'].create({
            'name': 'Cost Centre Test', 'code': 'CCTST', 'type': 'general', 'company_id': company.id,
        })
        distribution = {f'{accounts[0].id},{accounts[2].id}': 60,
                        f'{accounts[1].id},{accounts[2].id}': 40}

        def entry(date, amount, post=True):
            move = self.env['account.move'].create({
                'journal_id': journal.id, 'date': date,
                'line_ids': [
                    Command.create({'name': 'Expense', 'account_id': expense.id,
                                    'debit': max(amount, 0), 'credit': max(-amount, 0),
                                    'analytic_distribution': distribution}),
                    Command.create({'name': 'Offset', 'account_id': offset.id,
                                    'credit': max(amount, 0), 'debit': max(-amount, 0)}),
                ],
            })
            if post:
                move.action_post()
                self.assertEqual(move.state, 'posted')
                self.assertEqual(str(move.date), date)
                self.assertTrue(move.line_ids.analytic_line_ids, move.line_ids.mapped('analytic_distribution'))

        entry('2026-04-10', 1000)
        entry('2026-04-11', -100)
        entry('2025-04-10', 200)
        entry('2026-04-12', 999, post=False)
        entry('2026-05-01', 500)
        wizard = self.env['cost.center.expense.wizard'].create({
            'date_from': '2026-04-01', 'date_to': '2026-04-30',
            'cost_plan_id': cost_plan.id, 'city_plan_id': city_plan.id,
        })
        data = wizard._report_data()
        self.assertEqual(data['total'], {'actual': 900, 'previous': 200})
        self.assertEqual([g['actual'] for g in data['groups']], [540, 360])
        self.assertEqual(data['groups'][0]['code'], '110-211')
        self.assertEqual(data['format_amount'](-100), '(100.00)')
        expense.name = '=1+1'
        self.assertIn('=1+1', self._assert_excel_totals(wizard, 900, 200))
        wizard.action_preview()
        self.assertIn('Last Year', wizard.preview)
        wizard.write({'code_from': '110-211', 'code_to': '110-211'})
        self.assertEqual(wizard._report_data()['total']['actual'], 540)
        self._assert_excel_totals(wizard, 540, 120)
        wizard.write({'code_from': False, 'code_to': False})
        wizard.cost_center_ids = accounts[0]
        self.assertEqual(wizard._report_data()['total']['actual'], 540)
        wizard.write({'date_from': '2027-04-01', 'date_to': '2027-04-30'})
        self.assertEqual(wizard._report_data()['total'], {'actual': 0, 'previous': 540})
        self._assert_excel_totals(wizard, 0, 540)
        wizard.write({'date_from': '2029-04-01', 'date_to': '2029-04-30'})
        self.assertIn('No entries found', self._assert_excel_totals(wizard, 0, 0))
        with self.assertRaises(ValidationError), self.cr.savepoint():
            wizard.date_from = '2029-05-01'
import base64
import io
from zipfile import ZipFile
from xml.etree import ElementTree as ET
