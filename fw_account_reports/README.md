# Optix Accounting Reports — Odoo 19

Seven reports appear directly under **Accounting → Reporting**, with HTML preview, PDF and CSV exports. Install `fw_account_reports`; dependencies are `account` and `analytic`. Access requires Accounting read-only privileges or an accounting role that inherits them. ORM record rules remain active.

| Report | Calculation |
| --- | --- |
| Age Analysis ACP | Posted payable journal items through the as-of date, with partial reconciliations through that date. Includes currently reconciled bills if open at cutoff. Buckets use maturity date: not due, due today, 1–30, 31–60, 61–90, 91–120, 121–150, >150. Advances/debits appear separately without aging buckets, matching the sample. |
| Cost Centre-wise Income | Posted income/other-income analytic allocations, grouped by cost centre, optional city and ledger account. Same period last year. Negates analytic amounts to show credit revenue in parentheses. Unallocated income is outside this report. |
| List of Payments (All) | Posted outbound supplier payments with journal entries, grouped by bank. Gross = payable debit, net = liquidity credit. Classified payment journal credits supply WHT/STSP. Other = gross − net − deductions. Knock-off uses reconciliations through end date. Balance = unmatched gross. |
| List of Payments (Taxes) | Payments with nonzero WHT/STSP. Taxable amount defaults to gross unless specified. Rate defaults to effective WHT/base unless stated. Balance = net less gross knock-off, allowing negative values as in the sample. |
| Sales Tax Annexure - AP | One row per posted vendor bill/refund selected by accounting date, displaying invoice date. Base/taxes use company-currency ledger balances; refunds reverse values. Multiple tax names share one row to avoid duplicating base. Quantities are summed only for a common UOM. |
| Supplier Balances | Opening payable balance before start date, debit/credit within period, closing = opening + debit − credit. Optional zero-balance suppliers. Supplier reference supplies the legacy code. |
| Transaction List | Journal items grouped by month, journal, date and voucher with subtotals. Posted by default; draft-and-posted option available. Account/partner filters can select only part of a voucher. |

All money is in the selected company's currency. Sample transactions are not imported. Income/supplier PDFs use A4 portrait; wide reports use A3 landscape. Column headers repeat across pages. Legacy SHerp version strings and unused Analysis1–5 labels are omitted.

## Field mapping and setup

- Set **Accounting Report Tax Category** on ledger accounts for WHT, STSP/PRT, sales tax, extra tax, FED and noncreditable input tax. WHT/STSP accounts can also be selected on each report. Existing `purchase_inherit` income-tax account mappings are recognized when present.
- Partner **Tax ID** supplies NTN; **Report CNIC** overrides existing `cnic_number` when available. Set **Annexure Supplier Type**, province/state and city on the partner. Missing data prints blank.
- Vendor bill **AP Report Details** provides tax challan status, HS code, purchase type, PRT type and deduction document/date.
- Payment **Payment Tax Report Details** provides optional taxable base in company currency, stated WHT rate and payment nature. Cheque number uses the standard cheque field when installed, otherwise payment reference.

Payment tax deductions must appear on the payment journal entry. Deductions recorded only on bills are not automatically attributed in full to partial payments. The existing custom payment registration code is unchanged. Annexure classifies bill ledger amounts; deduction-document metadata is entered on the bill. Configure account categories and missing legacy metadata before relying on these columns.

CSV exports raw signed monetary numbers (supplier balances debit positive, aging totals credit positive). Text starting with spreadsheet formula characters is escaped. Exports include title, company, currency, dates, columns and subtotals.

## Tests

On a disposable database:

```sh
odoo -d optix_reports_test -i fw_account_reports --without-demo \
  --test-enable --test-tags /fw_account_reports --workers 0 --stop-after-init --no-http
```

Tests cover historical reconciliation, aging boundaries, advances, opening/movement/closing balances, income allocations and prior-year values, drafts, payment deductions, tax refunds, all seven previews, CSV escaping and company/date validation.
