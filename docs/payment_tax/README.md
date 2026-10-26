# Payment taxes and cheque advice

## Scope

Implemented in `purchase_inherit` (Purchase Control Hub), using the installed `fw_account_reports` module for account classification and payment tax reports. The workflow supports outgoing supplier payments, including payments entered directly without bills or PRs.

New tax payments store gross settlement, permanent deduction lines (tax, category, account, taxable base, configured rate, formula and calculated amount), supplier/payee, cheque date, and multiple invoice/PO/PR references. The standard payment amount is the **net bank payment**. All amounts use the payment currency and its rounding precision; journal debits and credits use company currency.

## Configuration applied

Accounting → Configuration → Taxes:

- `Payment Deduction Category`: WHT or Sales Tax / STSP.
- `Payment Deduction Account`: existing current-liability account for the relevant withholding authority.
- Existing percentage and custom-formula calculations are reused. Negative withholding percentages/formulas produce positive deduction amounts.
- Only taxes with a deduction category are selectable. Normal invoice sales tax remains on the bill and is not automatically deducted from payment.
- As authorized, tax 172, “IT Without Sales Tax Withheld 11%”, is corrected from 0% to 11%; tax 177, “IT Without Sales Tax Withheld 15%”, from 0% to 15%.

Accounting → Configuration → Chart of Accounts → Accounting Report Tax Category:

| Existing account ID | Account | Category |
|---|---|---|
| 567 | Tax withheld from payments to suppliers | WHT |
| 562 | FBR sales tax withheld from suppliers | STSP |
| 563 | SRB sales tax withheld from suppliers | STSP |
| 564 | PRA sales tax withheld from suppliers | STSP |
| 565 | KPK sales tax withheld from suppliers | STSP |

The corresponding deduction taxes are classified consistently; WHT taxes also receive the legacy `Is Income Tax` flag for report compatibility. See `configure.py` for the repeatable, assertion-guarded configuration script. It targets the audited Optix database IDs and must not be blindly reused on another database.

Existing bank journals' configured payment accounts are retained. A tax payment requires a payment method with an outstanding/payment account and a supplier with a payable account. Missing accounts produce an actionable error; accounts are not silently substituted. The existing “Tax Case” journal has no outgoing payment account configured and should not be used for these payments until Finance chooses its account.

## Process: payment against bills

1. Open the posted supplier bill, or select bills for one supplier and currency, and choose **Pay / Register Payment**.
2. Choose bank journal, payment method and date.
3. Enable **Payment Tax Deductions**.
4. Review **Gross Settlement**, initially the selected outstanding balance. For a partial payment, enter the gross portion being settled.
5. Add the applicable WHT and/or STSP taxes. Each line calculates automatically. `Use Gross as Base` applies the existing formula to the gross settlement; disable it and enter **Custom Tax Base** when required.
6. Keep **Payment Difference Handling → Keep Open**. The generated payment includes the tax credits, so full gross settlements reconcile in full; genuine partial settlements leave only the unpaid gross balance open.
7. When paying multiple bills, enable **Group Payments**. Different suppliers/currencies/payable-account batches must be registered separately when using tax deductions.
8. Create the payment. Invoice number/date, PO/bill reference and PR number are copied from linked documents when available. Partial gross allocations are apportioned by the selected bill residuals, with currency rounding.
9. Open the payment and choose **Print → Payment / Cheque Advice**.

Early-payment-discount write-offs are not combined with this deduction workflow. Do not select a payment deduction that has already been deducted on the bill.

## Process: standalone/manual payment without bills or PRs

1. Accounting → Vendors → Payments → New.
2. Select outgoing/vendor payment, supplier, bank journal, payment method and date.
3. Enable **Payment Tax Deductions** and enter **Gross Amount**.
4. Select the applicable deduction taxes and review their bases, rates, accounts and amounts. **Net Payable** and the standard **Amount** update automatically.
5. Enter payee name if different from the supplier, cheque date, and the standard cheque/payment reference and bank details.
6. In **Invoice / P.O. / PR References**, enter invoice number/date, PO/bill reference and PR number manually when known. Multiple rows are supported; their gross allocations must total the payment gross amount. If no references exist, the advice identifies it as a standalone payment.
7. Confirm the payment. The **Accounting Entries** table shows the actual debit/credit entries, also available through the standard journal-entry button.
8. Print **Payment / Cheque Advice**.

Selecting a bill in an advice-reference row is documentation only. It does not silently reconcile or modify a bill. Use Register Payment for automatic reconciliation, or the standard reconciliation tools to apply an existing standalone payment later.

## Accounting example

For gross PKR 100,000 and WHT 5.5% on that gross:

| Account | Debit | Credit |
|---|---:|---:|
| Supplier payable | 100,000.00 | 0.00 |
| WHT payable | 0.00 | 5,500.00 |
| Bank / configured outstanding payment account | 0.00 | 94,500.00 |

An STSP deduction adds a separate tax credit and reduces the bank credit further. It does not create a second expense or modify the original bill. Standalone payments create a supplier debit that can subsequently be reconciled to a bill.

Tax rates shown on formula taxes can differ from effective rates because existing formulas can extract sales tax from a tax-inclusive amount. Both rates are shown where configured; `Formula` is shown when a separate nominal rate is not configured. The formula snapshot is available as an optional column on the payment. Each deduction uses its own stated base. PKR calculations retain the database's existing currency rounding rather than forcing the sample advice's whole-rupee deduction.

## Development details

- Replaced the commented-out standalone payment implementation with permanent payment tax/reference models.
- Replaced the legacy wizard code that added unbalanced credits to the original bill. Tax credits are now supplied to Odoo's normal balanced payment-entry generation.
- Preserved core reconciliation, bank handling and foreign-currency conversion.
- Added gross/net calculations and editable taxable bases, plus saved rate/account/formula snapshots.
- Added manual references and automatic linked-bill/PO/PR extraction.
- Added payment form, accounting-entry display and a printable cheque-advice report with supplier/bank details, invoice references, gross, WHT, STSP, net, rates and actual debits/credits.
- Added accounting-user access and company rules for persistent detail lines. Inventory-administrator access is no longer required for accountants using the wizard.
- Added validation for zero/excessive deductions, missing/wrong-company tax accounts, duplicate taxes, unsupported batches, incorrect reference allocations and changes to posted details.
- Draft edits and reset/repost keep tax entries synchronized without duplicate tax credits. Posted advice is checked against journal amounts before printing.
- Added a narrowly scoped new-payment numbering fix: if imported old fiscal labels conflict with the payment date, the new tax-payment voucher uses the company's configured fiscal year through Odoo's standard sequence locking. Historical numbers are not rewritten.

The advice action is for payments using **Payment Tax Deductions**. Existing historical payments retain their original receipts; existing tax reports can classify their existing ledger entries using the newly configured account categories. No historical payment deductions are recalculated or retroactively reconstructed.

## Validation and maintenance

`validate.py` is an Odoo-shell integration suite restricted to database names beginning `optix_payment_tax_uat_`. It always rolls back its fixture transactions. It tests standalone and linked payments, custom bases, STSP formulas, no-tax payments, partial/grouped settlements, original-bill preservation, standard payment behavior, invalid inputs, reset/repost, foreign currencies, fiscal numbering, posted snapshot preservation, accounting-user permissions, reports and PDF rendering.

`sample_advice_uat.pdf` is an illustration generated from rolled-back UAT fixtures, not a live supplier transaction.

After deployment, refresh the browser. For additional deduction taxes, set both the deduction category and liability account, verify the calculation and taxable base, and assign the same report category to the account. Keep WHT and STSP on separate accounts for aggregate reporting.

The database backup made before this work is `/tmp/optix_before_payment_tax_20260930.dump`. A deployment-time backup and outcome record are documented in `deployment.md`. Restoring a full backup also rolls back any business transactions since that backup and therefore requires a planned restore window.
