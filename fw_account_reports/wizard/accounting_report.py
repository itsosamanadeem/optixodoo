import base64
import csv
import io
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


REPORTS = [('aging', 'Age Analysis ACP'), ('income', 'Cost Centre-wise Income'),
           ('payments', 'List of Payments (All)'), ('payment_taxes', 'List of Payments (Taxes)'),
           ('annexure', 'Sales Tax Annexure - AP (Summary)'),
           ('suppliers', 'Supplier Balances'), ('transactions', 'Transaction List')]


class AccountingReport(models.TransientModel):
    _name = 'fw.account.report.wizard'
    _description = 'Optix Accounting Report'

    report_type = fields.Selection(REPORTS, required=True, default='aging')
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)
    date_from = fields.Date(required=True, default=lambda s: fields.Date.context_today(s).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today, string='End / As of Date')
    target_moves = fields.Selection([('posted', 'Posted Entries'), ('all', 'Draft and Posted Entries')],
                                    required=True, default='posted')
    partner_ids = fields.Many2many('res.partner', string='Suppliers')
    journal_ids = fields.Many2many('account.journal', string='Journals / Banks')
    account_ids = fields.Many2many('account.account', 'fw_report_account_rel', string='Ledger Accounts')
    cost_plan_id = fields.Many2one('account.analytic.plan', string='Cost Centre Plan',
        default=lambda s: s.env['account.analytic.plan'].search([('name', 'ilike', 'Cost center')], limit=1))
    city_plan_id = fields.Many2one('account.analytic.plan', string='City Plan',
        default=lambda s: s.env['account.analytic.plan'].search([('name', 'ilike', 'City')], limit=1))
    cost_center_ids = fields.Many2many('account.analytic.account', 'fw_report_cost_rel', string='Cost Centres')
    city_ids = fields.Many2many('account.analytic.account', 'fw_report_city_rel', string='Cities')
    code_from = fields.Char('Cost Centre Code From')
    code_to = fields.Char('Cost Centre Code To')
    include_zero = fields.Boolean('Include Suppliers with Zero Balances')
    wht_account_ids = fields.Many2many('account.account', 'fw_report_wht_rel', string='WHT Accounts')
    stsp_account_ids = fields.Many2many('account.account', 'fw_report_stsp_rel', string='STSP / PRT Accounts')
    preview = fields.Html(readonly=True, sanitize=False)
    export_file = fields.Binary(readonly=True, attachment=False)
    export_filename = fields.Char(readonly=True)

    @api.onchange('company_id')
    def _onchange_company(self):
        self.journal_ids = self.account_ids = self.wht_account_ids = self.stsp_account_ids = False
        self.cost_center_ids = self.city_ids = False

    @api.onchange('cost_plan_id', 'city_plan_id')
    def _onchange_plans(self):
        self.cost_center_ids = self.city_ids = False

    @api.onchange('report_type', 'company_id', 'date_from', 'date_to', 'target_moves',
                  'partner_ids', 'journal_ids', 'account_ids', 'cost_plan_id', 'city_plan_id',
                  'cost_center_ids', 'city_ids', 'code_from', 'code_to', 'include_zero',
                  'wht_account_ids', 'stsp_account_ids')
    def _clear_preview(self):
        self.preview = False
        self.export_file = False

    def _validate_options(self):
        self.ensure_one()
        if self.company_id not in self.env.companies:
            raise AccessError(_('Select a company you have access to.'))
        if self.report_type != 'aging' and self.date_from > self.date_to:
            raise ValidationError(_('Start date must not be after end date.'))
        if self.report_type == 'income' and not self.cost_plan_id:
            raise ValidationError(_('Select the cost centre analytic plan.'))
        if self.city_plan_id and self.city_plan_id.root_id == self.cost_plan_id.root_id:
            raise ValidationError(_('Cost centre and city must use different analytic plans.'))
        if self.code_from and self.code_to and self.code_from > self.code_to:
            raise ValidationError(_('The starting code must not exceed the ending code.'))
        if self.wht_account_ids & self.stsp_account_ids:
            raise ValidationError(_('WHT and STSP accounts must not overlap.'))
        for records in (self.journal_ids, self.cost_center_ids, self.city_ids, self.partner_ids):
            if any(r.company_id and r.company_id != self.company_id for r in records):
                raise ValidationError(_('All filters must belong to the selected company or be shared.'))
        for account in self.account_ids | self.wht_account_ids | self.stsp_account_ids:
            if self.company_id not in account.company_ids:
                raise ValidationError(_('Select ledger accounts belonging to the report company.'))

    def _domain(self, period=True):
        domain = [('company_id', '=', self.company_id.id),
                  ('parent_state', 'in', ['draft', 'posted'] if self.report_type == 'transactions'
                   and self.target_moves == 'all' else ['posted'])]
        if period:
            domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        return domain

    def _lines(self, domain):
        return self.env['account.move.line'].with_company(self.company_id).search(domain, order='date, move_id, id')

    def _residuals_at(self, lines):
        # Reconstruct from original balances: today's residual would erase bills
        # paid after the historical report date. Never filter on reconciled=False.
        amounts = {line.id: line.balance for line in lines}
        if not lines:
            return amounts
        partials = self.env['account.partial.reconcile'].search([
            ('company_id', '=', self.company_id.id), ('max_date', '<=', self.date_to),
            '|', ('debit_move_id', 'in', lines.ids), ('credit_move_id', 'in', lines.ids)])
        for partial in partials:
            if partial.debit_move_id.id in amounts:
                amounts[partial.debit_move_id.id] -= partial.amount
            if partial.credit_move_id.id in amounts:
                amounts[partial.credit_move_id.id] += partial.amount
        return amounts

    def _category(self, line, legacy_wht_accounts=()):
        if line.account_id in self.wht_account_ids:
            return 'wht'
        if line.account_id in self.stsp_account_ids:
            return 'stsp'
        if line.account_id.fw_tax_category:
            return line.account_id.fw_tax_category
        tax = line.tax_line_id
        if tax and 'is_income_tax' in tax._fields and tax.is_income_tax:
            return 'wht'
        # The installed legacy payment wizard posts deductions without tax_line_id.
        if line.account_id.id in legacy_wht_accounts:
            return 'wht'
        return 'sales' if tax else False

    def _legacy_wht_accounts(self):
        taxes = self.env['account.tax']
        if 'is_income_tax' not in taxes._fields or 'account_id' not in taxes._fields:
            return []
        return taxes.search([
            ('company_id', '=', self.company_id.id), ('is_income_tax', '=', True),
            ('account_id', '!=', False)]).account_id.ids

    @staticmethod
    def _cnic(partner):
        return partner.fw_cnic or (partner.cnic_number if 'cnic_number' in partner._fields else '') or ''

    @staticmethod
    def _row(cells, kind='line'):
        return {'cells': cells, 'kind': kind}

    def _total(self, rows, columns, title='Total'):
        cells = [''] * len(columns)
        cells[0] = title
        for i, (_, kind) in enumerate(columns):
            if kind in ('money', 'balance'):
                cells[i] = sum(r['cells'][i] for r in rows if isinstance(r['cells'][i], (int, float)))
        return self._row(cells, 'total')

    def _aging(self):
        cols = [(n, 'text') for n in ['Transaction Date', 'Type', 'Document No.', 'Voucher Date',
                'Voucher Type', 'Voucher No.', 'Reference', 'Credit Days', 'Exact Days', 'Overdue Days',
                'Tax Challan Received', 'Narration']]
        cols += [(n, 'money') for n in ['Not Due', 'Due Today', '1–30 Days', '31–60 Days',
                 '61–90 Days', '91–120 Days', '121–150 Days', '>150 Days']]
        cols += [('Total', 'credit_balance')]
        lines = self._lines(self._domain(False) + [('date', '<=', self.date_to),
                                                ('account_id.account_type', '=', 'liability_payable')])
        residuals = self._residuals_at(lines)
        groups = defaultdict(lambda: [[], []])
        for line in lines:
            residual = residuals[line.id]
            if self.company_id.currency_id.is_zero(residual):
                continue
            move = line.move_id
            invoice_date = move.invoice_date or line.date
            due = line.date_maturity or line.date
            days = (self.date_to - due).days
            buckets = [0.0] * 8
            if residual < 0:
                bucket = 0 if days < 0 else 1 if days == 0 else min(7, 2 + (days - 1) // 30)
                buckets[bucket] = -residual
            cells = [invoice_date, dict(move._fields['move_type'].selection).get(move.move_type, move.move_type),
                     move.ref or move.name, line.date, line.journal_id.code, move.name, move.ref or '',
                     (due - invoice_date).days, (self.date_to - invoice_date).days, max(days, 0),
                     'Yes' if move.fw_challan_received else 'No', line.name or ''] + buckets + [-residual]
            groups[line.partner_id][residual > 0].append(self._row(cells))
        rows, detail = [], []
        for partner in sorted(groups, key=lambda p: (p.ref or '', p.name or '')):
            rows.append(self._row([f'Supplier ({partner.ref or ""}) {partner.name or "Unassigned"}'], 'group'))
            supplier = []
            for label, values in zip(['Outstanding Bills and Credit Documents', 'Unadjusted Payment and Debit Documents'], groups[partner]):
                if values:
                    rows.append(self._row([label], 'group'))
                    rows += values
                    total = self._total(values, cols, 'Total: ' + label)
                    total['cells'][-1] = sum(r['cells'][-1] for r in values)
                    rows.append(total)
                    supplier += values
            total = self._total(supplier, cols, 'Supplier Total')
            total['cells'][-1] = sum(r['cells'][-1] for r in supplier)
            rows.append(total)
            detail += supplier
        total = self._total(detail, cols, 'Grand Total')
        total['cells'][-1] = sum(r['cells'][-1] for r in detail)
        rows.append(total)
        return cols, rows

    def _suppliers(self):
        cols = [('Supplier Code', 'text'), ('Supplier', 'text'), ('Opening Balance', 'balance'),
                ('Debit', 'money'), ('Credit', 'money'), ('Closing Balance', 'balance')]
        totals = defaultdict(lambda: [0.0, 0.0, 0.0])
        for line in self._lines(self._domain(False) + [('date', '<=', self.date_to),
                                                     ('account_id.account_type', '=', 'liability_payable')]):
            values = totals[line.partner_id]
            if line.date < self.date_from:
                values[0] += line.balance
            else:
                values[1] += line.debit
                values[2] += line.credit
        if self.include_zero:
            domain = [('supplier_rank', '>', 0), '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)]
            if self.partner_ids:
                domain.append(('id', 'in', self.partner_ids.ids))
            for partner in self.env['res.partner'].search(domain):
                totals[partner]
        rows = []
        for partner in sorted(totals, key=lambda p: (p.ref or '', p.name or '')):
            opening, debit, credit = totals[partner]
            if not self.include_zero and all(self.company_id.currency_id.is_zero(v) for v in totals[partner]):
                continue
            rows.append(self._row([partner.ref or '', partner.name or 'Unassigned', opening,
                                   debit, credit, opening + debit - credit]))
        return cols, rows + [self._total(rows, cols, 'Grand Total')]

    def _income(self):
        cols = [('Account Code', 'text'), ('Title', 'text'), ('Actual', 'money'), ('Last Year', 'money')]
        cost_field = self.cost_plan_id._column_name()
        city_field = self.city_plan_id._column_name() if self.city_plan_id else None
        domain = [('company_id', '=', self.company_id.id), ('move_line_id.parent_state', '=', 'posted'),
                  ('general_account_id.account_type', 'in', ['income', 'income_other']),
                  (cost_field + '.plan_id', 'child_of', self.cost_plan_id.id)]
        if self.cost_center_ids:
            domain.append((cost_field, 'in', self.cost_center_ids.ids))
        if self.city_ids and city_field:
            domain.append((city_field, 'in', self.city_ids.ids))
        groupby = [cost_field] + ([city_field] if city_field else []) + ['general_account_id']
        totals = defaultdict(lambda: [0.0, 0.0])
        analytic = self.env['account.analytic.line'].with_company(self.company_id)
        for index, (start, end) in enumerate([(self.date_from, self.date_to),
                (self.date_from - relativedelta(years=1), self.date_to - relativedelta(years=1))]):
            for result in analytic._read_group(domain + [('date', '>=', start), ('date', '<=', end)], groupby, ['amount:sum']):
                cost, account = result[0], result[-2]
                city = result[1] if city_field else self.env['account.analytic.account']
                code = '-'.join(filter(None, [cost.code, city.code]))
                if (self.code_from and code < self.code_from) or (self.code_to and code > self.code_to):
                    continue
                # Analytic revenue is positive; the sample uses GL credit signs.
                totals[(code, '-'.join(filter(None, [cost.name, city.name])), account)][index] -= result[-1]
        groups = defaultdict(list)
        for (code, title, account), amounts in sorted(totals.items(), key=lambda v: (v[0][0], v[0][2].code or '')):
            if not all(self.company_id.currency_id.is_zero(v) for v in amounts):
                groups[(code, title)].append(self._row([account.code, account.name] + amounts))
        rows, detail = [], []
        for (code, title), values in groups.items():
            rows.append(self._row([code + ' ' + title + ' — Income'], 'group'))
            rows += values + [self._total(values, cols, 'Income'),
                              self._total(values, cols, '(Gain) / Loss for ' + title)]
            detail += values
        return cols, rows + [self._total(detail, cols, 'Total Gain / (Loss)')]

    def _payments(self):
        taxes_only = self.report_type == 'payment_taxes'
        cols = ([(n, 'text') for n in ['Payment Date', 'Cheque No.', 'On A/c Of', 'Payee']] +
                [('Gross Amount', 'money'), ('Taxable Amount', 'money'), ('WHT Rate (%)', 'rate'),
                 ('WHT', 'money'), ('STSP Amount', 'money'), ('Payment Amount', 'money'),
                 ('Balance Amount', 'money')] + [(n, 'text') for n in ['CNIC', 'Location', 'Payment Nature']]) if taxes_only else (
                [(n, 'text') for n in ['Doc. No.', 'Date', 'Cheque No.', 'On A/c Of', 'Payee', 'Voucher']] +
                [(n, 'money') for n in ['Gross Amount', 'WHT', 'STSP Amount', 'Payment Amount',
                                      'Other Transactions', 'Knocked-off Amount', 'Balance Amount']])
        domain = [('company_id', '=', self.company_id.id), ('date', '>=', self.date_from),
                  ('date', '<=', self.date_to), ('payment_type', '=', 'outbound'),
                  ('partner_type', '=', 'supplier'), ('move_id.state', '=', 'posted'),
                  ('state', 'not in', ['draft', 'canceled', 'rejected'])]
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        legacy_wht_accounts = self._legacy_wht_accounts()
        groups = defaultdict(list)
        payments = self.env['account.payment'].with_company(self.company_id).search(domain, order='date, id')
        residuals = self._residuals_at(payments.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable'))
        for payment in payments:
            liquidity, counterpart, other = payment._seek_for_lines()
            payable = counterpart.filtered(lambda l: l.account_id.account_type == 'liability_payable')
            gross = sum(payable.mapped('balance'))
            net = -sum(liquidity.mapped('balance'))
            wht = -sum(l.balance for l in other if self._category(l, legacy_wht_accounts) == 'wht')
            stsp = -sum(l.balance for l in other if self._category(l, legacy_wht_accounts) == 'stsp')
            if taxes_only and self.company_id.currency_id.is_zero(wht) and self.company_id.currency_id.is_zero(stsp):
                continue
            unmatched = sum(residuals.get(l.id, l.balance) for l in payable)
            matched = gross - unmatched
            partner = payment.partner_id
            cheque = (payment.check_number if 'check_number' in payment._fields else '') or payment.payment_reference or ''
            if taxes_only:
                taxable = payment.fw_taxable_base if payment.fw_taxable_base_set else gross
                rate = payment.fw_wht_rate or (100 * wht / taxable if taxable else 0)
                nature = payment.fw_payment_nature or ', '.join(other.filtered(lambda l: self._category(l, legacy_wht_accounts) == 'wht').mapped('name'))
                cells = [payment.date, cheque, partner.name or '', partner.name or '', gross, taxable,
                         rate, wht, stsp, net, net - matched, self._cnic(partner), partner.city or '', nature]
            else:
                cells = [payment.name, payment.date, cheque, partner.name or '', partner.name or '',
                         payment.move_id.name, gross, wht, stsp, net, gross - net - wht - stsp, matched, unmatched]
            groups[payment.journal_id].append(self._row(cells))
        rows, detail = [], []
        for journal in sorted(groups, key=lambda j: j.code):
            rows.append(self._row([journal.code + ' ' + journal.name], 'group'))
            rows += groups[journal] + [self._total(groups[journal], cols, 'Bank Total')]
            detail += groups[journal]
        return cols, rows + [self._total(detail, cols, 'Grand Total')]

    def _annexure(self):
        names = ['Sr #', 'Supplier NTN', 'Supplier CNIC', 'Supplier Name', 'Supplier Type', 'Supplier Province',
                 'Document Type', 'Document Number', 'Document Date', 'HS Code', 'Purchase Type', 'Rate',
                 'Quantity / Electricity Units', 'UOM', 'Value Excluding Sales Tax', 'Sales Tax / FED in ST Mode',
                 'Input Credit Not Allowed', 'Extra Tax', 'FED Payable', 'ST Withheld as WH Agent',
                 'STSP / PRT Deduction Doc Type', 'STSP / PRT Deduction Date', 'PRT Type']
        cols = [(n, 'money' if 14 <= i <= 19 else 'text') for i, n in enumerate(names)]
        domain = [('company_id', '=', self.company_id.id), ('state', '=', 'posted'),
                  ('move_type', 'in', ['in_invoice', 'in_refund']), ('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        moves = self.env['account.move'].with_company(self.company_id).search(domain, order='date, name, id')
        legacy_wht_accounts = self._legacy_wht_accounts()
        rows = []
        for index, move in enumerate(moves, 1):
            partner = move.partner_id
            products = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            tax_amounts = defaultdict(float)
            for line in move.line_ids:
                category = self._category(line, legacy_wht_accounts)
                if category:
                    tax_amounts[category] += -line.balance if category in ('wht', 'stsp') else line.balance
            units = products.product_uom_id
            quantity = sum(products.mapped('quantity')) * (-1 if move.move_type == 'in_refund' else 1) if len(units) <= 1 else ''
            rates = ', '.join(sorted(set(t.name for t in products.tax_ids)))
            supplier_type = dict(partner._fields['fw_supplier_type'].selection).get(partner.fw_supplier_type, '')
            purchase_type = dict(move._fields['fw_purchase_type'].selection).get(move.fw_purchase_type, '')
            rows.append(self._row([index, partner.vat or '', self._cnic(partner), partner.name,
                supplier_type, partner.state_id.name or '', 'Credit Note' if move.move_type == 'in_refund' else 'Bill',
                move.ref or move.name, move.invoice_date or move.date, move.fw_hs_code or '', purchase_type, rates,
                quantity, units.name if len(units) == 1 else 'Mixed' if units else '', sum(products.mapped('balance')),
                tax_amounts['sales'], tax_amounts['noncredit'], tax_amounts['extra'], tax_amounts['fed'], tax_amounts['stsp'],
                move.fw_deduction_doc_type or '', move.fw_deduction_date or '', move.fw_prt_type or '']))
        return cols, rows + [self._total(rows, cols, 'Grand Total')]

    def _transactions(self):
        cols = [('Date', 'text'), ('Sr. No.', 'text'), ('Account Code', 'text'), ('A/c Description', 'text'),
                ('Voucher / Transaction Narration', 'text'), ('Debit', 'money'), ('Credit', 'money'), ('Reference', 'text')]
        groups = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
        for line in self._lines(self._domain()):
            groups[line.date.strftime('%Y-%m')][line.journal_id][line.date][line.move_id].append(line)
        rows, detail = [], []
        for period, journals in sorted(groups.items()):
            rows.append(self._row(['Period: ' + period], 'group'))
            period_rows = []
            for journal, dates in sorted(journals.items(), key=lambda v: v[0].code):
                rows.append(self._row(['Voucher Type: ' + journal.code + ' ' + journal.name], 'group'))
                journal_rows = []
                for date, moves in sorted(dates.items()):
                    date_rows = []
                    for move, lines in moves.items():
                        rows.append(self._row([f'{move.name or "/"} | {move.state.title()} | {move.ref or ""} | Created by: {move.create_uid.name}'], 'group'))
                        values = [self._row([l.date, i, l.account_id.code, l.account_id.name,
                                  l.name or move.ref or '', l.debit, l.credit, move.ref or move.payment_reference or ''])
                                  for i, l in enumerate(lines, 1)]
                        rows += values + [self._total(values, cols, 'Total for voucher: ' + (move.name or '/'))]
                        date_rows += values
                    rows.append(self._total(date_rows, cols, 'Total for: ' + str(date)))
                    journal_rows += date_rows
                rows.append(self._total(journal_rows, cols, 'Total for voucher type: ' + journal.code))
                period_rows += journal_rows
            rows.append(self._total(period_rows, cols, 'Total for period: ' + period))
            detail += period_rows
        return cols, rows + [self._total(detail, cols, 'Grand Total')]

    def _report_data(self):
        self._validate_options()
        wizard = self.with_company(self.company_id)
        method = '_payments' if self.report_type in ('payments', 'payment_taxes') else '_' + self.report_type
        cols, rows = getattr(wizard, method)()
        return {'title': dict(REPORTS)[self.report_type], 'columns': cols, 'rows': rows,
                'numeric_start': next((i for i, c in enumerate(cols) if c[1] in ('money', 'balance', 'credit_balance')), 1),
                'generated': fields.Datetime.context_timestamp(self, fields.Datetime.now()),
                'has_lines': any(r['kind'] == 'line' for r in rows)}

    def _format_cell(self, value, kind):
        if value is False or value is None or value == '':
            return ''
        if kind in ('money', 'balance', 'credit_balance', 'rate') and isinstance(value, (int, float)):
            if self.company_id.currency_id.is_zero(value):
                value = 0.0
            amount = format(abs(value), ',.6f' if kind == 'rate' else ',.2f')
            if kind in ('balance', 'credit_balance'):
                credit = value < 0 if kind == 'balance' else value > 0
                return amount + (' Cr' if credit else ' Dr')
            return '(' + amount + ')' if value < 0 else amount
        return str(value)

    def action_preview(self):
        self.ensure_one()
        self.preview = Markup(self.env['ir.qweb']._render('fw_account_reports.document', {'docs': self}))
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
                'view_mode': 'form', 'target': 'current', 'name': dict(REPORTS)[self.report_type]}

    def action_print(self):
        self._validate_options()
        action = 'report_portrait' if self.report_type in ('income', 'suppliers') else 'report_landscape'
        return self.env.ref('fw_account_reports.' + action).report_action(self, config=False)

    def action_export(self):
        data = self._report_data()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([data['title'], self.company_id.name, self.company_id.currency_id.name])
        writer.writerow(['As of' if self.report_type == 'aging' else 'From',
                         str(self.date_to if self.report_type == 'aging' else self.date_from), 'To', str(self.date_to)])
        writer.writerow([c[0] for c in data['columns']])
        for row in data['rows']:
            # Prevent spreadsheet formula execution from imported partner names/references.
            writer.writerow(["'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v
                             for v in row['cells']])
        self.export_filename = self.report_type + '_' + str(self.date_to) + '.csv'
        self.export_file = base64.b64encode(output.getvalue().encode('utf-8-sig'))
        return {'type': 'ir.actions.act_url', 'url': '/web/content/?model=%s&id=%s&field=export_file&filename_field=export_filename&download=true' % (self._name, self.id), 'target': 'self'}
