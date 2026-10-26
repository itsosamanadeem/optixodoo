# Optix Odoo 19 — Complete Customization and User Access Guide

Version 1.0 | Prepared 12 October 2026 | Audience: business users, managers, Finance, SCM, Inventory and administrators

## 1. Purpose and scope

This document describes the functionality present in the Optix custom-addons repository, explains where a person can use it in Odoo, and records the setup needed for each workflow. It covers all 12 addon directories in this workspace, including local modifications currently present in the working tree.

The descriptions are based on module manifests, models, views, security definitions and existing implementation documents. Repository presence establishes that code exists; it does not prove that every module is installed, configured or active in the production database. Production installation status and current user permissions were not checked for this document. Menu labels can vary with Odoo edition, language and installed applications. Where a standard parent menu is supplied by Odoo, the path below identifies the relevant application and record.

Custom Optix business functionality is distinguished from adapted or integrated third-party addons. Existing third-party author and license declarations remain applicable. No business transactions or application code were changed while preparing this guide.

## 2. Quick access directory

| Customization | Where a user accesses it | Primary user |
| --- | --- | --- |
| Purchase, internal and revenue share requests | Purchase Request app → open or create a request → Request Type and Products | Requesters and approvers |
| Project approval and planned products | Project app → open a project → Project Products and Approvals | Project managers and assigned approvers |
| Project PR | Purchase Request app → Request Type: Project PR → Project | Project requesters |
| Department-based analytic allocation | Request or purchase order → product lines → Departments / Analytic Distribution | Requesters and SCM |
| Department master setup | Employees → Departments → open department | HR / administrators |
| Product GL, asset tag and warranty duration | Inventory or Purchase → Products → product form | Product administrators |
| Purchase budget controls | Accounting → analytic budgets → Configuration; Purchase → RFQ → Confirm | Finance and SCM |
| Filter budget lines | Open a budget → Filter Lines | Finance |
| PO approval and recommendation | Purchase → Orders → RFQs / Purchase Orders → open order | SCM and assigned approvers |
| Approval group configuration | Purchase → Configuration → Approval Groups | CEO group |
| Return a PO to its source PR | Purchase → open order → Return PR | SCM User |
| Customized purchase order print | Purchase → open order → Print → Purchase Order | SCM |
| Customer code and CNIC | Contacts → open a contact | Contact users |
| CRM customer synchronization | Inventory → Operations → Deliveries → open delivery → Sync CRM Customers | Inventory users |
| CRM access-key setup | Inventory → Configuration → Settings → Optix CRM | System administrators |
| Delivery customer CNIC and product tags | Inventory → open transfer / delivery | Inventory users |
| Serial spreadsheet import | Inventory → transfer → product move / serial detail → Import Serials XLSX, when shown | Inventory users |
| Lot warranty and repair warranty | Inventory → Products → Lots/Serial Numbers; Repairs → repair form | Inventory and repair users |
| Gate pass / issuance receipt | Inventory → transfer → Consume/Issuance Receipt tab; Print → Gate Pass | Warehouse users |
| Payment deductions and cheque advice | Accounting → Vendors → Payments, or bill → Pay / Register Payment | Finance |
| Seven Optix accounting reports | Accounting → Reporting → select report | Accounting readers and Finance |
| Cost Centre-wise Expenses | Accounting → Reporting → Cost Centre-wise Expenses | Accounting readers and Finance |
| Dynamic accounting reports | Accounting → Reporting → Dynamic Financial Reports | Finance |
| Accounting kit reports and tools | Accounting → Reporting, Accounting, Configuration, Customers and Payments | Finance |
| Automatic backup configuration | Settings → Technical → Automatic Database Backup → Backup Configuration | Administrators |
| Inactive session timeout | Settings → Technical → Parameters → System Parameters | Administrators |
| Inventory column search | Supported Inventory list views → column-header filter row | Inventory users |

## 3. Purchase Request customization

Implemented primarily in Purchase Control Hub (purchase_inherit).

The standard Approvals application is renamed Purchase Request. Requests support Purchase Request, Internal Request and Revenue Share Request; the Project PR extension adds another request type. The request shows calculated amount and status, departmental product lines, analytic allocation and links to resulting purchase orders or internal transfers.

### Purchase Request workflow

1. Open Purchase Request and create a request using the configured purchase approval category.
2. Select Purchase Request as the request type. Enter the reason, required attachments and product lines.
3. Choose each line's department, product, quantity and unit. Review the description, price and analytic allocation. Non-service prices are derived from product cost; service prices can be entered manually.
4. Submit the request. The customization adds required department managers as approvers where they are not already listed. Each manager must be an employee with a linked Odoo user. Newly added department managers share an approval sequence so they can act in parallel.
5. Assigned approvers review the request. Department-manager refusal affects that manager's departmental lines and records the refusing user and date. A request can become Partial Approved.
6. Once eligible, use the Purchase Request action on the approved request to generate RFQs / purchase orders. This button creates purchasing documents; it is separate from submitting the request.
7. Open the resulting orders through the purchase-order smart button and complete the PO approval process.

Only eligible, non-refused lines without an existing purchase-order-line link are generated. Lines are grouped by supplier and company; a draft or sent order for the same request and supplier can receive additional eligible lines. Department, analytics, request price and reason pass to the order, and request attachments are copied when a new order is created. Supplier setup on products is required for order generation.

The request includes cancellation, withdrawal and reset behavior. Resetting clears the manager-refusal metadata. Approval activities are tied to the relevant request/approver, with customized activity completion behavior.

### Internal Request workflow

Use Request Type: Internal Request, add departmental product lines and submit for approval. After full or partial approval, use Create IR. Eligible consumable-type product lines are grouped by department and create internal stock transfers. Configure the departmental destination location before use. The request's Internal Transfer smart button opens its linked transfer, and generated transfers retain the source request reference. Repeated creation for the same request is checked to avoid duplicate transfers. Service lines do not generate stock transfers.

### Revenue Share Request

The request model includes Revenue Share Request and a Project field linked to won CRM opportunities, visible to the HR Revenue Share group. The PO-generation code carries a revenue-share flag for this type. However, the current request view exposes the order-generation button only for Purchase Request and Project PR. Treat revenue-share order generation as requiring a confirmed live entry point before training users on an end-to-end process. The revenue-share Project field is a CRM opportunity, separate from the Project app project used by Project PR.

## 4. Departments, products and analytic allocation

Open Employees → Departments and configure Cost Center, City and Department Location. Cost Center and City selectors use analytic plans whose names contain the corresponding text. Assign a department manager with a linked user and link requesting employees to their Odoo users.

Open a product through Inventory or Purchase. The product Accounting area adds an analytic GL selector using plans whose names contain GL. General Information adds Asset Tag No. and the warranty duration field, currently labelled Warrent and shown for serial-tracked products. Duration is interpreted as days. New products without an internal reference receive a reference from the product sequence.

Request and PO lines use department cost centre, department city and product GL to populate analytic distribution. The custom analytic widget supports the purchasing workflow. On PO lines, Amount to Change adjusts the non-service unit price relative to product standard cost; service lines remain manually editable. Changing the department can refresh the analytic allocation, so review it before approval.

## 5. Purchase orders, approvals and budget controls

Purchase orders add Department, Revenue Share, Reason, source Approval Request, department-manager approval tracking and a Sent Back flag. New RFQs use a custom RFQ sequence; confirmation can replace an RFQ-prefixed number with a purchase-order sequence number. Company currency is supplied when missing.

### Multi-level PO approval

1. A CEO-group user opens Purchase → Configuration → Approval Groups.
2. Define the group, ordered active levels, assigned users, recommendation/approval flags and amount limits.
3. On the RFQ, choose the approval group and confirm when ready.
4. Where approval is required, the order enters To Approve and shows the Current Approval Level and Pending At information.
5. Assigned users use Recommend or Returned as applicable and enter comments in the wizard. The final approval follows the available approval action.
6. Review Approval Comments for the history of requests, recommendations, returns and approvals.

Routing follows active level sequence. Maximum amount influences approval-button eligibility. Do not assume the configured minimum amount independently selects a routing band: the current level-routing implementation advances by sequence.

### Analytic budget control at confirmation

Purchase Control Hub extends Odoo's analytic budget models, budget.analytic and budget.line. Finance configures a confirmed budget for the cost centre / city / analytic GL combination and chooses Configuration: Restrict, Allow or Show only warning.

At PO confirmation, missing department city, product GL, analytic city or matching confirmed budget prevents confirmation. Restrict blocks an over-budget line; Show only warning opens a Budget Warning dialog with Proceed/Cancel; Allow permits exceeding the configured amount after the required setup checks.

The current comparison uses each PO line subtotal against the matching budget line's budget_amount. It is not a cumulative project-spend calculation. The city and GL lookups use database-specific analytic fields x_plan6_id and x_plan8_id. Preserve the corresponding analytic-plan structure when deploying elsewhere.

Open an analytic budget and choose Filter Lines to filter by cost centre, city, GL, product, exact start/end dates and budget amount using equals, greater-than-or-equal or less-than-or-equal. The date fields match exact line dates rather than filtering an overlapping period.

### Return and manager review

SCM User can use Return PR on a PO with a valid source request reference. It cancels the order, withdraws/cancels/resets the source PR and schedules an activity for the requester. The requester revises and resubmits the request. Orders with no identifiable source PR cannot use this process.

Manager Approval records the current department manager's approval on the order. The approval code includes a check for all department managers on returned orders with Amount to Change lines. Availability depends on the record's workflow and the user's role.

### Purchase order print

Use the standard Purchase Order print action. The customized layout includes requester, origin under PROJ/CUSTOMER Name & Code, delivery/payment terms, quote reference, delivery date, business unit, internal department and delivery location. Lines show item code, description, quantity, unit, unit price and extended price. Totals, amount in words and fixed Optix terms are added. Discount and Other Charges currently print as fixed 0.00 values; the project/customer label displays origin rather than a separate customer lookup.

## 6. Project approvals and Project PR budgets

Implemented in Project PR Budget Control (project_pr_budget).

1. Open a project in the Project app. Add Project Products with planned product, quantity, UoM and estimated unit cost.
2. Select an Approval Group and use Submit for Approval.
3. Assigned users approve sequentially. The Approvals tab records level status, acting user and action date. Authorized users can reject; Project Managers have the Reset to Draft action.
4. After approval, open the project's Purchase Requisitions smart button or create a Purchase Request with Request Type: Project PR and select the approved project.
5. Choose products from the project's planned items and review planned, requested and remaining quantity plus estimated unit cost.
6. Submit and approve the Project PR, then use the purchase-generation action to create purchasing documents.

The extension checks that the project is approved, the company matches where specified, products belong to the plan, and quantity and amount remain within the project limits. It checks committed requests during submission/approval and document creation. Committed states include approved, partially approved and purchasing/transfer-created requests; refused lines are excluded from active line consumption.

Project Total Cost is planned quantity × estimated cost. Utilized Amount is based on committed Project PR request amounts; Remaining Amount is planned cost less utilization. These figures represent request commitments, not posted expenses or payments. Submitted requests alone are not included in the committed-state total.

Tasks can only be created or moved into approved projects under this extension. Approved project budget information is protected from ordinary users; Project Managers can modify it. Changing the selected project on a draft Project PR clears its product lines, so choose the project before entering products.

## 7. Contacts and CRM customer synchronization

Contacts add an automatically sequenced Code and CNIC Number. CRM customer identity is stored separately from this internal code.

An administrator enters the CRM access key at Inventory → Configuration → Settings → Optix CRM and saves. Inventory users open an outgoing delivery and click Sync CRM Customers. A progress screen shows the import status and Return to receipt reopens the saved delivery with the updated customer selector. Leaving the screen does not stop the job.

The integration reads the Optix CRM customer endpoint in batches of 200. It creates or updates customers by unique CRM CustomerId and maps name, address, city, CNIC, email, phone, customer code, area, subarea, MRC and status. Imported blank contact values clear previous imported values. Customers absent from the response are not deleted, and CRM status does not automatically archive contacts.

The supplied schedule starts nightly at 02:00 Asia/Karachi; a worker scheduled every minute processes pending work. Actual timings can be edited in Settings → Technical → Automation → Scheduled Actions. Cron workers must be enabled. A failed run resumes from the first uncommitted page; clicking again after completion starts a full scan. One shared job prevents overlapping imports.

Existing contacts without CRM IDs are not automatically matched by name, phone or CNIC. Link existing records to their CRM identities before the first scan where necessary to prevent duplicate business contacts. Users do not enter credentials on the delivery form.

## 8. Inventory, serials, warranty and gate passes

Transfers display aggregated product internal references, asset tags and the selected customer's CNIC. Outgoing delivery customer selection is limited to contacts marked as customers.

### Serial spreadsheet import

Open the product move / serial-detail area of a transfer and use Import Serials XLSX when available. Upload an .xlsx workbook whose first row is a header. Accepted headers are serial, serial number and serial_no; otherwise the first column is used. The active sheet is read and the first row is skipped.

Import fills existing movement-detail rows in order and creates additional detail rows for extra serials. Values populate the custom Serial Number field (serial_no); they do not automatically create Odoo lot records or populate the standard lot/serial linkage. Check movement quantities and standard lot assignment before validation. The import requires openpyxl. Additional-row creation uses qty_done in the current code, so verify that branch on the deployed Odoo 19 database before relying on bulk creation.

### Warranty and repairs

Products store warranty duration in days. On creation of a lot for a product with a duration, missing warranty start defaults to today and missing end becomes start plus duration. Open Inventory → Products → Lots/Serial Numbers to review Warrenty Start, Warrenty End and Warrenty Status (current spelling in the interface).

Repairs displays the selected lot's warranty status and updates the repair's under-warranty choice when the lot is selected. Warranty status is stored and recomputes when its date fields change; the code does not contain a daily expiry-refresh job, so stored status should not be assumed to update solely because midnight passes.

### Gate pass / Consume/Issuance Receipt

Open a transfer's Consume/Issuance Receipt tab and enter vehicle number, driver name, driver contact and corresponding company. Created By records the originating user and Include Product Details controls whether product details are printed. Use Print → Gate Pass to generate the receipt. The interface tab is renamed; the print action remains Gate Pass. This addon retains Cybrosys attribution and includes local receipt presentation changes.

## 9. Supplier payment deductions and cheque advice

Implemented in Purchase Control Hub, with account classifications and reporting supplied by fw_account_reports.

Finance configures Accounting → Configuration → Taxes with Payment Deduction Category (WHT or Sales Tax / STSP) and Payment Deduction Account. Configure Accounting Report Tax Category on the corresponding ledger accounts. Supplier payable and journal outgoing payment/outstanding accounts must be present. Normal bill sales tax stays on the bill; only designated withholding taxes are selectable for payment deductions.

### Payment against bills

1. Open a posted vendor bill or select bills for one supplier and currency, then choose Pay / Register Payment.
2. Select journal, payment method and date; enable Payment Tax Deductions.
3. Review Gross Settlement. For a partial settlement, enter the gross portion being paid.
4. Add WHT/STSP taxes. Keep Use Gross as Base or disable it and enter Custom Tax Base.
5. Keep Payment Difference Handling: Keep Open. For multiple bills use Group Payments; register incompatible supplier, currency or payable-account batches separately.
6. Create the payment, review its journal entry, then choose Print → Payment / Cheque Advice.

### Standalone payment

Open Accounting → Vendors → Payments → New. Choose an outgoing supplier payment, enable Payment Tax Deductions and enter Gross Amount. Review deductions and Net Payable. Add payee/cheque details and optional Invoice / P.O. / PR References. Multiple reference rows are supported and their allocated gross amounts must total the payment gross. Confirm and print Payment / Cheque Advice.

Net bank payment = gross settlement − deductions. For example, gross 100,000 with 5.5% WHT produces supplier payable debit 100,000, WHT credit 5,500 and bank/outstanding payment credit 94,500. The original bill is preserved. A standalone payment can later be reconciled through standard accounting tools; selecting a bill in an advice-reference row only documents that reference.

Persistent deduction lines retain tax, account, category, base, rate, formula and amount snapshots. Linked payments copy invoice/PO/PR references when available. Accounting Entries displays actual journal amounts. The advice shows supplier/bank details, references, gross, WHT, STSP, net and actual debits/credits. Validation checks duplicate taxes, invalid accounts, excessive deductions, reference totals and posted changes. Draft/reset/repost behavior synchronizes deduction entries.

Early-payment-discount write-offs are not combined with this workflow. Avoid deducting a tax already deducted on the bill. Existing historical deductions are not reconstructed. Database-specific tax corrections and account mappings are recorded in docs/payment_tax; those IDs must not be applied blindly to another database.

## 10. Optix accounting reports

### Seven reports in fw_account_reports

Open Accounting → Reporting, choose a report, set company and date filters, then use View Report, Print PDF or Export CSV. Access requires Accounting read-only privileges or a role that inherits them; company and record access rules still apply.

| Report menu | What it provides |
| --- | --- |
| Age Analysis ACP | Payables outstanding at an as-of date, historical reconciliation effects and maturity buckets; advances separately |
| Cost Centre-wise Income | Posted income analytic allocations by cost centre, optional city and account, with same-period prior-year comparison |
| List of Payments (All) | Posted outbound supplier payments grouped by bank, gross/net, WHT/STSP, other differences and knock-off/balance |
| List of Payments (Taxes) | Payments with WHT/STSP, taxable amount, rates, payment nature and report-specific balance |
| Sales Tax Annexure Report | Posted vendor bills/refunds, taxable base and tax classifications, invoice/supplier and deduction metadata |
| Supplier Balances | Opening payable balance, period debits/credits and closing balance; optional zero balances |
| Transaction List | Journal items by month, journal, date and voucher, with subtotals and optional draft entries |

Set tax categories on ledger accounts, partner Tax ID/Report CNIC/Annexure Supplier Type and location details, bill AP Report Details, and payment Payment Tax Report Details where needed. Reports display money in selected company currency. Bill-only deductions are not automatically attributed in full to partial payments.

### Cost Centre-wise Expenses

Open Accounting → Reporting → Cost Centre-wise Expenses. Set dates, company, cost centre plan, optional city plan/cities, code bounds and printed site heading. Use View Report, Print PDF or Export Excel for a native .xlsx workbook.

The report includes posted journal-linked analytic allocations for expense, depreciation and cost-of-revenue accounts. Credits reduce expense; the same calendar dates one year earlier provide Last Year. Unallocated journal items and manual analytic items without a posted journal entry are excluded. Prior-year-only accounts remain visible.

Cost centre/city analytic Reference values form combined codes; names form headings. Inclusive code bounds filter those codes. Site Heading changes printed text; Company and Cities filter data. Excel contains numeric amounts, groups, subtotals and grand totals. Sum account detail rather than detail plus subtotal rows to avoid double counting.

### Dynamic Financial Reports

The integrated Cybrosys dynamic_accounts_report addon exposes Accounting → Reporting → Dynamic Financial Reports: General Ledger, Trial Balance, Partner Ledger, Balance Sheet, Profit and Loss, Cash Book, Bank Book, Aged Receivable, Aged Payable and Tax Report. It supplies interactive report screens and export/print controls according to each screen. This family is separate from the seven Optix-format reports above.

## 11. Accounting kit and community budget integration

base_accounting_kit is a Cybrosys Community accounting addon included in the repository. It supplies:

- Accounting → Reporting → Generic Statements: Profit and Loss, Balance Sheet and Cash Flow Statement.
- Accounting → Reporting → Daily Reports: Cash Book and Bank Book.
- Accounting → Reporting → Partner Reports: Partner Ledger and Aged Partner Balance.
- Accounting → Reporting → Audit Reports: General Ledger, Trial Balance, Journals Audit and Tax Report.
- Accounting → Accounting → Management: asset records and depreciation operations.
- Accounting → Configuration: asset categories, account groups, financial report definitions and follow-up levels.
- Customer follow-up reports and contact Customer Statement information.
- Recurring Templates under the payment menu; recurring-entry automation.
- Bank-statement import/reconciliation, credit-limit settings, post-dated cheque support, invoice copy-layout configuration and accounting lock-date tools, where enabled.

These are integrated package capabilities, not all original Optix developments. Availability depends on installed dependencies, roles and accounting configuration.

base_account_budget adds the separate Community budget workflow. Open Accounting → Accounting → Budgets, enter budget lines and use Confirm, Approve and Done as appropriate. Configuration includes budgetary positions/accounts, analytic accounts show Budget Items, and Filter Lines opens the added filtering wizard.

Community budgets use crossovered.budget models. They are separate from Purchase Control Hub's account_budget analytic budget models and from Project PR commitments. Configuring one does not automatically configure the others.

## 12. Administration and supporting modules

### Automatic database backup

The integrated auto_database_backup addon provides Settings → Technical → Automatic Database Backup → Backup Configuration (enable developer mode to access Technical). Configure database, format, destination, credentials, retention and notifications. Destination choices include local storage, FTP/SFTP, Google Drive, Dropbox, OneDrive, Nextcloud and Amazon S3. Connection-test buttons are available for supported destinations. Scheduled Actions controls the job execution.

The existing backup documentation includes configuration and operational evidence, logs and a staging listing from 6 October 2026. It records SFTP authentication and backup startup and an archive visible in the supplied listing; it does not establish a current restore test. See docs/auto_database_backup/Auto_Database_Backup_Configuration.pdf for the operational record.

### Inactive session timeout

auth_session_timeout is an OCA addon that expires inactive sessions. Configure Settings → Technical → Parameters → System Parameters: inactive_session_time_out_delay (seconds) and inactive_session_time_out_ignored_url (excluded technical URLs). The supplied default delay is two hours. Ordinary users experience this through session expiry rather than a separate menu.

### Advanced inventory list search

jl_list_advance_search_inventory adapts supported Inventory list renderers for the separate jl_list_advance_search base module. Install the base dependency and enable advanced search in user preferences where required. Use the filter row beneath column headings, combining text/relation filters or numeric/date ranges with native search and grouping. The base module is not in this workspace; this inventory addon alone does not provide the complete search feature.

## 13. Roles and setup responsibilities

| Role | Responsibility / access |
| --- | --- |
| Requester | Enter requests and departmental lines; submit and follow approval status |
| Department manager | Review departmental lines and assigned approval activities; linked employee/user required |
| Raise PR Request for all Departments | Broader department selection than the ordinary requester domain |
| SCM User / SCM Manager | Purchasing processing; non-revenue-share PO access rules; SCM User has Return PR |
| CEO | Approval Groups menu and broad purchase-order access through custom group rules |
| HR Revenue Share | Visibility of the CRM-opportunity Project field on requests |
| Project Manager | Project planning and permitted changes/reset of approved project information |
| Assigned project/PO approver | Act at the configured current approval level |
| Inventory user | Transfers, delivery customer sync and stock operations subject to normal access |
| Accounting reader / Finance | Reports; accounting users manage permitted payments and deduction details |
| System administrator | Users, CRM key, module installation, schedules, backup and session parameters |

Assign roles in Settings → Users & Companies → Users. Custom PO rules cover employee ownership/assignment, department-manager association, SCM non-revenue-share visibility and CEO full domain. Odoo combines applicable group rules and inherited groups; validate actual visibility with the intended user's account instead of treating a single rule as an exclusive restriction.

Before rollout, verify module installation, department managers/users, analytic plans and budget combinations, product supplier/cost/GL data, project plans, approval levels, supplier/bank accounts, deduction categories and report metadata. Users should refresh their browsers after backend asset upgrades.

## 14. Module and source register

| Technical addon | Coverage / attribution |
| --- | --- |
| purchase_inherit | Purchase Control Hub; Osama Nadeem / Zalino Tech; requests, purchasing, analytics, master data, CRM sync, warranty, serial import and payment deductions |
| project_pr_budget | Project PR Budget Control; Zalino Tech; project planning/approval and request commitment limits |
| ml_purchase_approval | Multi-level PO approval groups, levels, actions and history; integrated with Purchase Control Hub |
| fw_account_reports | Seven Optix-format accounting reports and supporting metadata |
| cost_center_expense_report | Expense reporting with prior-year comparison and PDF/Excel output |
| gatepass_slip | Cybrosys gate pass addon with local receipt/interface customization |
| base_account_budget | Cybrosys Community budgets with filtering extension |
| base_accounting_kit | Cybrosys Community accounting package |
| dynamic_accounts_report | Cybrosys interactive accounting reports |
| auto_database_backup | Cybrosys automated backup integration |
| auth_session_timeout | OCA inactive-session expiration |
| jl_list_advance_search_inventory | Third-party inventory compatibility extension for advanced list search |

Primary implementation sources: each addon's __manifest__.py, models, views, wizards, reports and security files. Detailed references: docs/crm_customer_sync.md; docs/payment_tax/README.md and deployment.md; fw_account_reports/README.md; cost_center_expense_report/README.md; docs/uat/Optix_Accounting_Reports_UAT_v1.0.pdf; docs/auto_database_backup/README.md; auth_session_timeout/readme/CONFIGURE.md; jl_list_advance_search_inventory/README.md.

Existing test sources cover the seven accounting reports, expense reports and CRM sync; the payment-tax documentation contains an isolated Odoo-shell validation suite. Those tests were not rerun for this documentation-only task. The access paths and behavioral descriptions were checked against repository definitions; live installation, screen visibility and transaction behavior remain deployment checks.
