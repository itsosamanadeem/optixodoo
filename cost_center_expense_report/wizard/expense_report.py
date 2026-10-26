import base64
import io
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from markupsafe import Markup
import xlsxwriter

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class CostCenterExpenseWizard(models.TransientModel):
    _name = 'cost.center.expense.wizard'
    _description = 'Cost Centre-wise Expenses'

    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)
    date_from = fields.Date(required=True, default=lambda s: fields.Date.context_today(s).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    cost_plan_id = fields.Many2one(
        'account.analytic.plan', string='Cost Centre Plan', required=True,
        default=lambda s: s.env['account.analytic.plan'].search([('name', 'ilike', 'Cost center')], limit=1),
    )
    city_plan_id = fields.Many2one(
        'account.analytic.plan', string='City Plan',
        default=lambda s: s.env['account.analytic.plan'].search([('name', 'ilike', 'City')], limit=1),
    )
    cost_center_ids = fields.Many2many('account.analytic.account', 'cc_expense_cost_rel', string='Cost Centres')
    city_ids = fields.Many2many('account.analytic.account', 'cc_expense_city_rel', string='Cities')
    code_from = fields.Char(string='Cost Centre Code From')
    code_to = fields.Char(string='Cost Centre Code To')
    site_name = fields.Char(string='Site Heading', default=lambda s: s.env.company.name,
                            help='Printed heading; accounting entries are filtered by Company and Cities.')
    preview = fields.Html(readonly=True, sanitize=False)
    excel_file = fields.Binary(readonly=True, attachment=False)
    excel_filename = fields.Char(readonly=True)

    @api.onchange('cost_plan_id', 'city_plan_id', 'company_id')
    def _onchange_dimensions(self):
        self.cost_center_ids = False
        self.city_ids = False
        self.site_name = self.company_id.name

    @api.onchange('date_from', 'date_to', 'cost_plan_id', 'city_plan_id', 'company_id',
                  'cost_center_ids', 'city_ids', 'code_from', 'code_to', 'site_name')
    def _clear_preview(self):
        self.preview = False
        self.excel_file = False

    @api.constrains('date_from', 'date_to', 'cost_plan_id', 'city_plan_id', 'code_from', 'code_to')
    def _check_options(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_('The start date must not be after the end date.'))
            if wizard.city_plan_id and wizard.city_plan_id.root_id == wizard.cost_plan_id.root_id:
                raise ValidationError(_('Cost centre and city must use different analytic plans.'))
            if wizard.code_from and wizard.code_to and wizard.code_from > wizard.code_to:
                raise ValidationError(_('The starting cost centre code must not exceed the ending code.'))

    def _report_data(self):
        self.ensure_one()
        self._check_options()
        if self.company_id not in self.env.companies:
            raise AccessError(_('Select a company you have access to.'))
        cost_field = self.cost_plan_id._column_name()
        city_field = self.city_plan_id._column_name() if self.city_plan_id else None
        domain = [
            ('company_id', '=', self.company_id.id),
            ('move_line_id.parent_state', '=', 'posted'),
            ('general_account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']),
            (cost_field + '.plan_id', 'child_of', self.cost_plan_id.id),
        ]
        if self.cost_center_ids:
            domain.append((cost_field, 'in', self.cost_center_ids.ids))
        if self.city_ids and city_field:
            domain.append((city_field, 'in', self.city_ids.ids))
        groupby = [cost_field] + ([city_field] if city_field else []) + ['general_account_id']
        totals = defaultdict(lambda: [0.0, 0.0])
        periods = [(self.date_from, self.date_to),
                   (self.date_from - relativedelta(years=1), self.date_to - relativedelta(years=1))]
        analytic = self.env['account.analytic.line'].with_company(self.company_id)
        for index, (start, end) in enumerate(periods):
            for row in analytic._read_group(domain + [('date', '>=', start), ('date', '<=', end)],
                                            groupby, ['amount:sum']):
                cost = row[0]
                city = row[1] if city_field else self.env['account.analytic.account']
                account = row[-2]
                # Analytic expenses are negative; the reference presents expenses as positive.
                totals[(cost, city, account)][index] -= row[-1]
        groups = {}
        currency = self.company_id.currency_id
        for (cost, city, account), amounts in totals.items():
            if all(currency.is_zero(amount) for amount in amounts):
                continue
            code = '-'.join(filter(None, [cost.code, city.code]))
            if (self.code_from and code < self.code_from) or (self.code_to and code > self.code_to):
                continue
            key = (cost.id, city.id)
            if key not in groups:
                groups[key] = {
                    'code': code,
                    'title': '-'.join(filter(None, [cost.name, city.name])),
                    'lines': [], 'actual': 0.0, 'previous': 0.0,
                }
            group = groups[key]
            group['lines'].append({'code': account.code, 'title': account.name,
                                   'actual': amounts[0], 'previous': amounts[1]})
            group['actual'] += amounts[0]
            group['previous'] += amounts[1]
        ordered = sorted(groups.values(), key=lambda g: (g['code'], g['title']))
        for group in ordered:
            group['lines'].sort(key=lambda line: line['code'] or '')
        # Fixed pages repeat the group heading when a cost centre spans pages.
        pages, rows = [], []
        for group in ordered:
            if len(rows) > 34:
                pages.append(rows)
                rows = []
            rows.append(dict(group, kind='group'))
            for line in group['lines']:
                if len(rows) >= 38:
                    pages.append(rows)
                    rows = [dict(group, kind='group')]
                rows.append(dict(line, kind='line'))
            if len(rows) > 36:
                pages.append(rows)
                rows = [dict(group, kind='group')]
            rows.extend([dict(group, kind='subtotal', title='Expense'),
                         dict(group, kind='subtotal', title='(Gain) / Loss for ' + group['title'])])
        total = {'actual': sum(g['actual'] for g in ordered),
                 'previous': sum(g['previous'] for g in ordered)}
        if len(rows) >= 38:
            pages.append(rows)
            rows = []
        rows.append(dict(total, kind='total', title='Total Gain / (Loss) :'))
        pages.append(rows)
        return {'pages': pages, 'groups': ordered, 'total': total,
                'generated': fields.Datetime.context_timestamp(self, fields.Datetime.now()),
                'format_amount': lambda n: ('(%s)' if n < 0 and not currency.is_zero(n) else '%s') % format(abs(n), ',.2f')}

    def action_preview(self):
        self.ensure_one()
        self.preview = Markup(self.env['ir.qweb']._render(
            'cost_center_expense_report.report_document', {'docs': self}))
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'current',
                'name': _('Cost Centre-wise Expenses')}

    def action_print(self):
        self.ensure_one()
        return self.env.ref('cost_center_expense_report.action_report_expenses').report_action(self)

    def _xlsx_content(self):
        data = self._report_data()
        output = io.BytesIO()
        # Imported names and codes must remain text, never formulas or links.
        with xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False,
                                          'strings_to_urls': False}) as workbook:
            sheet = workbook.add_worksheet('Cost Centre Expenses')
            sheet.hide_gridlines(2)
            sheet.set_column('A:A', 22)
            sheet.set_column('B:B', 60)
            sheet.set_column('C:D', 20)
            title = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'})
            meta = workbook.add_format({'font_color': '#526475', 'text_wrap': True, 'valign': 'top'})
            heading = workbook.add_format({'bold': True, 'bg_color': '#E8EFF5', 'bottom': 1})
            group_format = workbook.add_format({'bold': True, 'bg_color': '#E8EFF5', 'text_wrap': True})
            text = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            decimals = self.company_id.currency_id.decimal_places
            number_format = '#,##0' + ('.' + '0' * decimals if decimals else '')
            number_format += ';(' + number_format + ')'
            amount = workbook.add_format({'num_format': number_format})
            subtotal = workbook.add_format({'bold': True, 'top': 1, 'text_wrap': True})
            subtotal_amount = workbook.add_format({'bold': True, 'top': 1, 'num_format': number_format})
            sheet.merge_range(0, 0, 0, 3, self.company_id.name, title)
            sheet.merge_range(1, 0, 1, 3, 'Cost Centre-wise Expenses', title)
            metadata = [
                'Site: ' + (self.site_name or self.company_id.name),
                f'Period: {self.date_from} to {self.date_to} | Currency: {self.company_id.currency_id.name}',
                f'Last Year: {self.date_from - relativedelta(years=1)} to {self.date_to - relativedelta(years=1)}',
                'Cost Centre Plan: ' + self.cost_plan_id.name + ' | City Plan: ' + (self.city_plan_id.name or 'None'),
                'Cost Centres: ' + (', '.join(self.cost_center_ids.mapped('name')) or 'All'),
                'Cities: ' + (', '.join(self.city_ids.mapped('name')) or 'All'),
                f'Cost Centre Codes: {self.code_from or "First"} to {self.code_to or "Last"}',
                'Posted Entries | Generated: ' + data['generated'].strftime('%Y-%m-%d %H:%M') + ' | User: ' + self.env.user.name,
            ]
            for row, label in enumerate(metadata, 2):
                sheet.merge_range(row, 0, row, 3, label, meta)
                sheet.set_row(row, 30 if len(label) > 110 else 18)
            row = len(metadata) + 3
            sheet.write_row(row, 0, ['Account Code', 'Title', 'Actual', 'Last Year'], heading)
            sheet.freeze_panes(row + 1, 2)
            sheet.repeat_rows(row)
            row += 1
            for group in data['groups']:
                sheet.write_string(row, 0, group['code'] or '', group_format)
                sheet.merge_range(row, 1, row, 3, group['title'], group_format)
                row += 1
                for line in group['lines']:
                    sheet.write_string(row, 0, line['code'] or '', text)
                    sheet.write_string(row, 1, line['title'] or '', text)
                    sheet.write_number(row, 2, line['actual'], amount)
                    sheet.write_number(row, 3, line['previous'], amount)
                    row += 1
                for label in ('Expense', '(Gain) / Loss for ' + group['title']):
                    sheet.merge_range(row, 0, row, 1, label, subtotal)
                    sheet.write_number(row, 2, group['actual'], subtotal_amount)
                    sheet.write_number(row, 3, group['previous'], subtotal_amount)
                    row += 1
                row += 1
            if not data['groups']:
                sheet.merge_range(row, 0, row, 3, 'No entries found for the selected filters.', text)
                row += 1
            sheet.merge_range(row, 0, row, 1, 'Total Gain / (Loss) :', subtotal)
            sheet.write_number(row, 2, data['total']['actual'], subtotal_amount)
            sheet.write_number(row, 3, data['total']['previous'], subtotal_amount)
            sheet.set_landscape()
            sheet.set_paper(9)
            sheet.fit_to_pages(1, 0)
            sheet.print_area(0, 0, row, 3)
            sheet.set_footer('Page &P of &N')
        return output.getvalue()

    def action_export_excel(self):
        self.ensure_one()
        self.excel_file = base64.b64encode(self._xlsx_content())
        self.excel_filename = f'Cost_Centre_Expenses_{self.date_from}_{self.date_to}.xlsx'
        return {'type': 'ir.actions.act_url', 'target': 'self',
                'url': f'/web/content/?model={self._name}&id={self.id}&field=excel_file'
                       '&filename_field=excel_filename&download=true'}
