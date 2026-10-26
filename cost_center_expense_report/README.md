# Cost Centre-wise Expenses

Open Accounting > Reporting > Cost Centre-wise Expenses. Select the dates,
company, cost centre plan and optional city plan, then View Report, Print PDF,
or Export Excel to download a native `.xlsx` workbook.
The same calendar dates one year earlier supply the Last Year column.

The report uses posted journal-linked analytic items for expense, depreciation,
and cost-of-revenue accounts. Analytic allocation amounts are preserved; credits
reduce expenses. Unallocated journal items and manual analytic items without a
posted journal entry are excluded. Accounts present only in the previous period
are retained. Amounts use the selected company's currency.

Cost centre and city analytic Reference fields form codes such as `110-211`;
their names form the group title. Optional code bounds apply inclusively to the
combined code. Populate Reference fields to reproduce legacy codes. The Site
Heading is printed text; Company and Cities control which entries are included.
Company name and logo come from Odoo, and the footer identifies the Odoo user.

The Letter PDF follows the supplied expense report's columns, centre/city
grouping, subtotals, negative amounts in parentheses, and repeated page headings.
The source PDF's transactions and legacy branding are not imported.

Excel uses the same filtered report data, including cost centre/city groups,
account detail, Actual and Last Year, subtotals and grand totals. Amounts remain
numeric for spreadsheet calculations; codes retain leading zeroes and text is
not interpreted as formulas. The workbook includes filter headings, frozen
column headers and print settings. Subtotals are presentation rows: sum account
detail only when doing your own calculations, to avoid counting totals twice.

Run Odoo's test runner with `--test-tags /cost_center_expense_report` to verify
split allocations, credits, posting state, date boundaries, comparison periods,
code filters, preview rendering, Excel totals and text safety, empty exports,
and invalid date handling. Fixtures are rolled
back and use their own company to avoid existing accounting lock dates.
