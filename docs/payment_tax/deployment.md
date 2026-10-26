# Deployment record — 30 September 2026

Database: `LIVE_3_AGUST_2026-1147AM` (local Docker deployment).

The tested `purchase_inherit` upgrade was applied with the web service stopped. `configure.py` then classified existing withholding accounts and taxes and corrected the two approved rates. The transaction was committed and Odoo was restarted.

## Preserved business data

Before/after checksums match for the audited payment and accounting values:

| Dataset | Rows | Matching MD5 |
|---|---:|---|
| Payments | 237 | `65934e9a124d4cf0d02d39736db4b7be` |
| Journal entries | 616 | `cce994ffe316876535f1253b33ba1931` |
| Journal lines | 2,551 | `6e9d71c7197e102c4aaef27022b00da9` |

See `fingerprint.sql` for the exact fields compared. No live test payments or journal entries were created. Existing bank/payment account assignments and historical voucher numbers were retained.

## Applied configuration

- Account 567: WHT reporting category.
- Accounts 562, 563, 564, 565: STSP reporting category.
- Corresponding withholding tax records: payment deduction category and income-tax flag.
- Tax 172: 11%; tax 177: 15%, explicitly authorized by the user.
- New payment fields, accountant access, company rules, wizard and advice report installed.

Company fiscal-year end remains the pre-existing January 1 setting: no specific alternative was confirmed. The new tax-payment numbering safeguard uses the configured year boundary and generates date-valid new vouchers even when old imported numbers carry mismatched year labels. Finance can confirm the proper fiscal-year boundary separately; existing entries are not resequenced by this implementation.

The existing `Tax Case` journal lacks an outgoing payment account. It remains unchanged; the new workflow gives a configuration error if it is selected without an account.

## Validation

17 integration checks passed on the isolated database copy, covering standalone and linked payments, custom tax bases, STSP formulas, no-tax payments, full/partial/grouped reconciliation, preserved bill lines, standard payment regression, invalid inputs, reset/repost, foreign currencies, existing JS bank numbering, saved rate snapshots, normal accountant access, PDF generation and existing tax reporting.

The report was also visually reviewed. The UAT fixture transactions were rolled back. The sample PDF is retained as a demonstration only.

## Backup and rollback material

- Initial database backup: `/tmp/optix_before_payment_tax_20260930.dump`
- Fresh backup immediately before live deployment: `/tmp/optix_payment_tax_predeploy_20260930.dump`
- Original tracked payment source: `/tmp/optix_payment_tax_original_source_20260930.tar.gz`
- Live upgrade log: `/tmp/optix_payment_tax_live_upgrade.log`
- Before/after fingerprints: `/tmp/optix_payment_tax_before.txt`, `/tmp/optix_payment_tax_after.txt`

Backups are outside the repository. Move them to managed backup storage if long-term retention is required. A rollback would require a maintenance window, restoration of the database and corresponding original source, and a restart. A full restore would discard transactions entered after the backup; do not restore over newer business activity without a recovery plan.
