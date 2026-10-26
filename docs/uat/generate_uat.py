"""Build the client UAT pack using only Python's standard library."""
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

OUT = Path(__file__).parent
NAME = 'Optix_Accounting_Reports_UAT_v1.0'
NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def p(text='', style=None, bold=False, size=None):
    props = '<w:pPr>' + (f'<w:pStyle w:val="{style}"/>' if style else '') + '</w:pPr>'
    rp = ('<w:b/>' if bold else '') + (f'<w:sz w:val="{size}"/>' if size else '')
    return f'<w:p>{props}<w:r><w:rPr>{rp}</w:rPr><w:t xml:space="preserve">{escape(str(text))}</w:t></w:r></w:p>'


def table(headers, rows, widths):
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    result = ['<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblLayout w:type="fixed"/><w:tblBorders>' +
              ''.join(f'<w:{s} w:val="single" w:sz="4" w:color="CED6DE"/>' for s in ['top','left','bottom','right','insideH','insideV']) +
              '</w:tblBorders><w:tblCellMar><w:top w:w="75" w:type="dxa"/><w:left w:w="95" w:type="dxa"/><w:bottom w:w="75" w:type="dxa"/><w:right w:w="95" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>' + grid + '</w:tblGrid>']
    for index, row in enumerate([headers] + rows):
        result.append('<w:tr><w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if index == 0 else '') + '</w:trPr>')
        for width, cell in zip(widths, row):
            shade = '<w:shd w:fill="E8EFF5"/>' if index == 0 else ''
            paragraphs = cell if isinstance(cell, list) else [cell]
            result.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shade}</w:tcPr>')
            for item in paragraphs:
                for line in str(item).split('\n'):
                    result.append(p(line, 'Cell', bold=index == 0))
            result.append('</w:tc>')
        result.append('</w:tr>')
    result.append('</w:tbl>')
    return ''.join(result)


pages = []
def page(title, subtitle=''):
    content = p(title, 'Title')
    if pages:
        content = content.replace('<w:pPr>', '<w:pPr><w:pageBreakBefore/>', 1)
    if subtitle:
        content += p(subtitle, 'Subtitle')
    pages.append(content)


def add(text, style=None):
    pages[-1] += p(text, style)


def grid(headers, rows, widths=(2500, 7600)):
    pages[-1] += table(headers, rows, widths)


REPORTS = [
 ('R01','Age Analysis ACP','Age Analysis ACP.pdf',6),
 ('R02','Cost Centre-wise Income','Cost Center Wise Report Income.pdf',7),
 ('R03','List of Payments (All)','List of Payment (All).pdf',8),
 ('R04','List of Payments (Taxes)','List of Payment (Taxes).pdf',9),
 ('R05','Sales Tax Annexure Report','Sales Tax Annexure Report.pdf',10),
 ('R06','Supplier Balances','Supplier Balances.pdf',11),
 ('R07','Transaction List','Transaction List.pdf',12),
]
all_cases = []

page('USER ACCEPTANCE TESTING', 'Accounting Reports | Client execution and sign-off pack')
add('Optix Pakistan Private Limited', 'Heading1')
add('Odoo 19 · Accounting → Reporting', 'Heading2')
add('Document ID: OPTIX-UAT-ACC-001    |    Version: 1.0    |    Issue date: 30 September 2026')
add('Status: Issued for client UAT — acceptance pending', 'Callout')
grid(['Document control','Details'],[
 ('Client / legal entity','Optix Pakistan Private Limited — confirm at sign-off'),
 ('Project / delivery','Seven custom Accounting reports'),
 ('Module / baseline','Optix Accounting Reports (fw_account_reports), version 19.0.1.0.0'),
 ('Release / commit tested','____________________________________________'),
 ('Prepared by / organisation','____________________________________________'),
 ('Client UAT owner','____________________________________________'),
 ('UAT environment / database','____________________________________________'),
 ('Execution dates','From: __________________  To: __________________'),
 ('Final decision','To be completed by the client on page 15'),
])
add('Purpose', 'Heading1')
add('Provide a repeatable, evidence-based record that the seven delivered reports meet the client’s agreed business requirements. This pack records test execution, discrepancies, agreed exceptions and the final acceptance decision.')
add('Completion instructions', 'Heading1')
add('Complete the environment and baseline before testing. Execute every applicable test, record actual results and evidence, log defects, and obtain the approvals on the final page. Blank fields do not constitute a pass or acceptance. Developer verification does not replace client UAT.')
add('Confidential — for the client and authorised implementation team.', 'Small')

page('01  Scope and reference documents', 'Navigation: Accounting → Reporting')
grid(['ID','Report / reference sample','Test page'],[(r[0],[r[1],r[2]],str(r[3])) for r in REPORTS],(700,8400,1000))
add('Included in this acceptance', 'Heading1')
add('Report access and filters; calculation rules; grouping and totals; on-screen preview; PDF printing and CSV export; supplier and tax metadata; company access restrictions; empty results and validation messages. Each report is assessed against Odoo source transactions and the reference sample’s business content.')
add('Reference comparison', 'Heading1')
add('The supplied PDFs establish expected columns and report structure. Their historical figures are not imported by the reporting module. Numeric comparison to a legacy PDF is valid only when the client confirms that company, transactions, balances, date basis and filters match. Attach a reconciliation for any remaining difference.')
add('Scope boundaries requiring acknowledgement', 'Heading1')
add('This delivery does not include legacy transaction migration, automatic repair of existing journal postings, changes to the payment-registration process, tax filing/submission, or a legal certification of tax treatment. Existing expense reporting is outside these seven reports. Exact SHerp branding, version labels and unused Analysis1–5 labels are not reproduced.')
add('Pack index', 'Heading1')
add('Readiness: page 3 · Business-rule approval: page 4 · Common tests: page 5 · Report tests: pages 6–12 · Results: page 13 · Defects/exceptions: page 14 · Sign-off: page 15.')

page('02  UAT readiness and execution', 'Client UAT lead completes this page before execution')
grid(['Readiness item','Confirmed details / owner'],[
 ('Environment','URL: __________________  Database: __________________\nCompany: __________________  Currency: __________________'),
 ('Baseline','Module version: 19.0.1.0.0  Release/commit: __________________\nData snapshot / refresh date: __________________'),
 ('People and access','UAT tester(s): __________________  Finance reviewer: __________________\nAccounting user and restricted user available: Yes / No'),
 ('Accounting data','Bills, credit notes, advances, partial/final payments, opening balances, draft/posted entries, foreign-currency transactions and multiple bank journals identified.'),
 ('Analytic data','Cost centre and city plans configured; allocated income and same-period prior-year data available.'),
 ('Tax mapping','WHT, STSP/PRT, sales tax, extra tax, FED and noncreditable input-tax accounts reviewed. Attach approved mapping and account codes.'),
 ('Supplier / bill data','NTN/Tax ID, CNIC, supplier type, province/city, HS code, purchase type, challan and PRT deduction details reviewed.'),
 ('Evidence location','Shared folder / reference: ________________________________________'),
 ('Readiness approval','Name: __________________  Date: __________________  Ready: Yes / No'),
])
add('Execution method', 'Heading1')
add('1. Use an approved UAT database or controlled test company. The examples are test fixtures, not instructions to enter artificial transactions into live accounts. Record the actual document IDs used.')
add('2. For each case, open the named report, apply the stated filters, select View Report and compare to independently checked Odoo journal items. Exercise PDF/CSV where specified.')
add('3. Record Pass, Fail, Blocked or N/A, actual figures/observations, evidence reference, tester and date. N/A requires a written reason and client UAT lead approval.')
add('4. Log every discrepancy on page 14. After a fix, retain the original evidence and attach retest results with the changed release identifier.')
add('Evidence naming: test ID + run/date + output type, e.g. AGE-01_2026-09-30_PDF. Amounts below use the selected company currency; the fixture period is April 2026 unless stated.', 'Small')

page('03  Business rules for client approval', 'Review before signing; disagreements become defects or agreed changes')
grid(['Rule','Delivered behavior / acceptance point'],[
 ('BR-01 · Currency and dates','Monetary totals use posted company-currency ledger amounts. Date ranges include both endpoints. Accounting date selects ledger/annexure entries; payment date selects payments. Aging uses an as-of date.'),
 ('BR-02 · Aging','Residuals reflect reconciliations effective through the cutoff, not today’s residual alone. Maturity date drives buckets. Outstanding credits are aged; unadjusted payments/debits are shown separately and reduce the net total.'),
 ('BR-03 · Income','Uses income/other-income analytic allocations to the chosen cost centre plan and optional city. Unallocated income is excluded. Revenue credits appear in parentheses; prior year is the same date range one year earlier.'),
 ('BR-04 · All Payments','Only posted outbound supplier payments with journal entries. Gross = payable debit; payment = liquidity credit. Other transactions = gross − payment − WHT − STSP. Knocked-off amount is reconciled gross through end date. Balance = gross − knocked-off amount.'),
 ('BR-05 · Tax Payments','Only payments with nonzero WHT/STSP. Taxable base defaults to gross unless specified on the payment; rate defaults to effective WHT/base unless a stated rate is supplied. Balance = net payment − gross knocked-off amount; it can be negative and differs from All Payments.'),
 ('BR-06 · Deduction source','Payment tax deductions are taken from classified payment journal lines. A tax recorded only on a bill is not automatically assigned to each partial payment. Correct account mappings/postings are required.'),
 ('BR-07 · Annexure','One row per posted vendor bill/credit note, not a rate-by-rate supplier consolidation. Tax names share the row. Refunds reverse amounts. Mixed-UOM quantities are not summed. Missing metadata stays blank; HS/purchase/PRT classifications are entered on the bill.'),
 ('BR-08 · Transactions and export','Transaction List can include drafts by explicit choice; other reports use posted entries. Account/partner filters may show only part of a voucher. CSV contains signed numbers; supplier debit balances are positive and aging credit totals are positive.'),
 ('BR-09 · Layout','Income and Supplier Balances use A4 portrait; wide reports use A3 landscape. Column headers repeat in PDFs. Client confirms the adapted layout and available filter set are suitable.'),
],(1950,8150))
add('Finance reviewer: __________________  Date: __________________', 'Small')
add('Decision: [ ] Rules accepted   [ ] Accepted with listed exceptions   [ ] Changes required', 'Small')
add('Exception / change references: __________________________________________________', 'Small')

def cases(rows):
    formatted = []
    for code, title, steps, expected in rows:
        all_cases.append(code)
        formatted.append((code,[title,'Steps: '+steps,'Expected: '+expected],['Status: ______','Actual: ______','____________','Evidence: ____','Tester/date: ___']))
    grid(['Test ID','Procedure and expected result','Execution record'],formatted,(850,7400,1850))


page('04  Common acceptance tests', 'Run applicable checks for each of the seven reports; attach a per-report result sheet')
cases([
 ('GEN-01','Menus and initial opening','With an accounting-authorised user, open each report from Accounting → Reporting.','All seven named entries open their correct filter forms without an Owl/asset/server error.'),
 ('GEN-02','Scope and filters','Select a company, date range and available supplier/journal/account filters. Change filters after previewing.','Only matching records appear. Preview clears after a filter change and refreshes on View Report. No results from another company are disclosed.'),
 ('GEN-03','Access control','Use a user without accounting access and an accounting user restricted to one company.','Unauthorised reports cannot be accessed. Restricted users cannot retrieve another company’s report through the UI or a direct request.'),
 ('GEN-04','Input validation','Use start date after end date on a period report; select an account in both WHT and STSP filters. On Income, select the same root plan for cost/city.','A clear validation message prevents generation. Aging requires only its as-of date, not a start/end comparison.'),
 ('GEN-05','Empty results','Choose a valid period/filter with no matching entries.','Preview, PDF and CSV complete without an error; report indicates no entries and totals are zero.'),
 ('GEN-06','PDF layout','Print each report, including a long narrative and a dataset spanning multiple pages.','Correct title, company, currency and dates; readable columns; no clipped amounts; repeated column headings and page numbers; totals match preview.'),
 ('GEN-07','CSV integrity','Export each report and reconcile detail/subtotal/grand total values to preview. Check a harmless fixture name beginning with =.','File opens with identifiable headers and signed numeric amounts. No duplicate counting of subtotals. Formula-like text is escaped; Cr/Dr display converts to documented numeric signs.'),
 ('GEN-08','Currency and response time','Run a foreign-currency transaction and a representative normal-volume dataset. Record volume and elapsed times.','Amounts match company-currency ledger balances. No timeout. Client agrees acceptable response times: preview ___ s; PDF ___ s; CSV ___ s; volume ___ rows.'),
])

FORMULAS = {
    5: [
        'For each payable journal item: B = debit − credit. Historical residual R = B − reconciled amounts on its debit side + reconciled amounts on its credit side, including only matches whose latest accounting date is on/before the cutoff. Report Total T = −R (positive = Cr; negative = Dr).',
        'Days overdue D = as-of date − maturity date (fallback: journal-item date). Credit days = maturity date − invoice date; exact days = as-of date − invoice date (invoice-date fallback: journal-item date). Displayed overdue days = max(D, 0).',
        'For R < 0, place −R in exactly one bucket: D < 0 Not Due; D = 0 Due Today; 1–30; 31–60; 61–90; 91–120; 121–150; D > 150. For R > 0, show an unadjusted debit without bucket values. Section/supplier/grand totals = sums of included values; net total = aged credits − unadjusted debits.',
    ],
    6: [
        'Actual for each cost-centre/city/account group = −Σ posted income/other-income analytic amounts within [start, end]. Where allocated at p%, analytic amount = source analytic income × p/100; use the stored allocation amount in the report.',
        'Last Year = −Σ eligible analytic amounts within [start − 1 calendar year, end − 1 calendar year], with the same filters. Leap-year dates follow calendar-year adjustment. Each group and grand total = Σ its account amounts. Negative figures print in parentheses; unallocated income is excluded.',
    ],
    7: [
        'G (gross) = Σ payable-line balances; N (net payment) = −Σ liquidity-line balances; W (WHT) = −Σ classified WHT deduction-line balances; S (STSP) = −Σ classified STSP deduction-line balances. Every line balance = debit − credit, in company currency.',
        'U = Σ historical residuals of payment payable lines through the end date (residual formula in Age Analysis). K (knocked-off) = G − U; Other Transactions = G − N − W − S; Balance = G − K = U. Bank and grand totals = sums of included payment rows.',
    ],
    8: [
        'Use G, N, W, S and K from the All Payments formulas. Include a row when W or S is nonzero at company-currency precision. Taxable base B = explicitly specified company-currency amount when its override is enabled; otherwise B = G.',
        'Displayed WHT rate = supplied nonzero stated rate; otherwise (W/B) × 100 if B ≠ 0, or 0 if B = 0. Displayed rate does not recompute the posted WHT amount. Balance = N − K; hence a fully matched payment may have a negative tax-report balance.',
        'Bank/grand amount totals = Σ included row amounts; rates are not summed. WHT/STSP amounts come from payment journal entries, not an inferred percentage applied to bills.',
    ],
    9: [
        'Per bill/credit note: Value Excluding Sales Tax = Σ balances of product-type invoice lines. Sales tax/FED-in-ST, noncreditable input, extra tax and FED payable = Σ posted line balances assigned to each category. ST withheld as WH agent = −Σ STSP/PRT-classified line balances. Balance = debit − credit in company currency.',
        'Posted credit notes reverse the ledger signs; no second sign reversal or currency conversion is applied to monetary columns. With a common UOM, Quantity = Σ invoice-line quantities × (+1 for bill; −1 for credit note); mixed-UOM quantity is blank. Grand totals = Σ document amounts.',
        'Rate is the list of configured invoice tax names, not a calculated blended rate. No tax is recalculated from quantity × unit price × rate. Select documents by accounting date, display invoice date, and count the purchase base once per document.',
    ],
    10: [
        'Opening O = Σ(debit − credit) of matching posted payable lines dated before start. Period debit D = Σ debit and period credit C = Σ credit for start ≤ accounting date ≤ end. Closing = O + D − C.',
        'Positive opening/closing = Dr; negative = Cr; display the absolute amount with that suffix. Grand totals = Σ supplier amounts. CSV retains the signed number. All sums use the same company, supplier, journal and payable-account filters.',
    ],
    11: [
        'Line debit and credit = the stored company-currency debit/credit on each selected journal item. Voucher debit/credit = Σ included line debit/credit; date, journal, month and grand totals = Σ included detail amounts in their respective groups (do not add displayed subtotals again).',
        'For a complete balanced voucher, Σ debit − Σ credit = 0. Account/partner filters can select only part of the voucher, so filtered totals need not balance. Posted-only includes posted entries; Draft and Posted includes both, within the inclusive accounting-date range.',
    ],
}

def report_page(number, title, reference, columns):
    page(f'{number:02d}  {title}', 'Reference: '+reference)
    add('Tester/date: __________________  Company/currency: __________________', 'Small')
    add('Period / as-of date: __________________  Filters / source document IDs: __________________', 'Small')
    add('Key output checks: '+columns, 'Small')
    add('Calculation formulas', 'Heading2')
    for formula in FORMULAS[number]:
        add(formula, 'Small')


report_page(5,'Age Analysis ACP',REPORTS[0][2], 'Supplier groups; transaction/voucher references; maturity-related days; challan indicator; narration; eight aging buckets; section, supplier and grand totals; Cr/Dr signs.')
cases([
 ('AGE-01','Historical residual after later settlement','Use a 1,000 bill dated/due 31-Mar-2026, matched to 200 on 15-Apr and 800 on 05-May. Run as of 30-Apr, then 31-May.','30-Apr: outstanding 800 Cr in 1–30 days, even though currently settled. 31-May: bill is absent. Retain payment/reconciliation evidence.'),
 ('AGE-02','Every aging boundary','Using posted open bills, set maturities to −1, 0, 1, 30, 31, 60, 61, 90, 91, 120, 121, 150 and 151 days overdue at cutoff.','Future maturity → Not Due; 0 → Due Today; 1/30 → 1–30; 31/60 → 31–60; 61/90 → 61–90; 91/120 → 91–120; 121/150 → 121–150; 151 → >150. Each item is counted once.'),
 ('AGE-03','Unadjusted advance and net supplier total','For a separate supplier, use a 1,000 unpaid bill and an unmatched 250 advance dated before cutoff.','Bill section = 1,000 Cr; advance section = 250 Dr with no aging-bucket allocation; net supplier total = 750 Cr.'),
 ('AGE-04','Filters, state and traceability','Filter one supplier/account/journal. Include draft and after-cutoff fixtures. Compare dates, narration, reference and challan status.','Only matching posted items through cutoff appear. Draft/future items are excluded. Details and credit/overdue days agree with source records.'),
 ('AGE-05','Independent reconciliation','For the same company, cutoff, supplier and payable accounts, compare aging net total with Supplier Balances closing balance. Review multiple maturity instalments if available.','Balances agree after translating sign conventions. All maturity lines are included once; bucket, section and grand totals reconcile. Explain and resolve differences.'),
])

report_page(6,'Cost Centre-wise Income',REPORTS[1][2], 'Cost centre/city groups; account code and title; Actual and Last Year; Income and group totals; grand total; parentheses for credit income.')
cases([
 ('INC-01','Allocated revenue and reversal','Post April income credit 1,000 and reversal debit 100, both split 60% to centre A and 40% to B. Run April.','Actual total = (900.00); A = (540.00); B = (360.00). Group/account totals preserve the allocation and GL sign.'),
 ('INC-02','Prior-year comparison','Use April 2025 income credit 200 with the same split. Run April 2026, then select only centre A.','Last Year total = (200.00); A = (120.00), B = (80.00). With A selected, Actual = (540.00), Last Year = (120.00).'),
 ('INC-03','City and code-range filters','Assign distinct city dimensions and cost centre codes. Select a city, individual centres and combined code range; test both boundaries.','Only the selected analytic dimensions and codes appear. Boundary codes are included; totals equal the included allocations.'),
 ('INC-04','Excluded and comparison-only records','Add draft income, posted income without the chosen plan, out-of-period income and an account with prior-year activity only.','Draft, unallocated and out-of-period values are excluded. Prior-year-only rows remain visible with zero Actual. Explain the difference from an unfiltered GL income total.'),
])
add('Finance confirmation: Analytic plan(s) and exclusion of unallocated revenue accepted: Yes / No', 'Callout')
add('Plan names / exception references: __________________________________________________')

report_page(7,'List of Payments (All)',REPORTS[2][2], 'Bank groups; payment date/document; cheque/reference; On A/c Of and payee; voucher; gross, WHT, STSP, net, other, knocked-off and balance amounts.')
cases([
 ('PAY-01','Gross-to-net and deductions','Create/identify a posted supplier payment journal: payable debit 1,000; bank/outstanding credit 850; WHT credit 100; STSP credit 50. Leave unmatched.','Gross 1,000; WHT 100; STSP 50; Payment 850; Other 0; Knocked-off 0; Balance 1,000. Amounts reconcile to the posted payment entry.'),
 ('PAY-02','Reconciliation cutoff','For the PAY-01 fixture, match 400 to a bill within April and the remaining 600 to a bill dated in May. Run April, then through May.','April: Knocked-off 400, Balance 600. Through May: Knocked-off 1,000, Balance 0. Later settlement does not alter the earlier cutoff result.'),
 ('PAY-03','Payment scope and bank subtotals','Include two bank journals, suppliers, a draft/cancelled payment, an inbound receipt and a payment without a posted journal. Apply bank/supplier filters.','Only eligible posted outbound supplier payments with journals appear. Excluded states/receipts do not contribute. Each bank subtotal and grand total equals included detail.'),
 ('PAY-04','Other deductions and document fields','Use a separate payment with gross 1,000, net 830, WHT 100, STSP 50 and an unclassified deduction 20. Check cheque/reference, supplier and voucher.','Other Transactions = 20. Identifiers trace to the payment and entry. On A/c Of and Payee both use the payment partner; client confirms this meets the requirement.'),
])
add('Approved WHT account(s): __________________  STSP account(s): __________________', 'Small')

report_page(8,'List of Payments (Taxes)',REPORTS[3][2], 'Payment date; cheque/reference; supplier/payee; gross; taxable amount; WHT rate and amount; STSP; net; balance; CNIC; location; payment nature.')
cases([
 ('TAX-01','Inclusion and tax-account classification','Use PAY-01 plus a tax-free payment and an STSP-only payment. Confirm report-level mappings and ledger categories.','PAY-01 and STSP-only payment appear; tax-free payment is excluded. WHT/STSP are taken from classified payment entries and agree with All Payments.'),
 ('TAX-02','Taxable base and rate','On PAY-01, first leave taxable-base override off, then set it to 800; finally supply a stated WHT rate of 10%.','Default base 1,000 → effective rate 10%. Specified base 800 → effective rate 12.5%. Stated 10% is displayed without changing the posted WHT amount of 100.'),
 ('TAX-03','Net balance semantics','Using net payment 850 and gross 1,000, run with matched amounts of 0, 400 and 1,000 effective by cutoff.','Balance equals 850, 450 and −150 respectively. Client explicitly accepts the net-minus-gross-knock-off calculation; it is different from All Payments.'),
 ('TAX-04','Metadata and bill-only deductions','Check partner CNIC/city and payment nature; test cheque fallback to payment reference. Use a separate bill-only withholding with no deduction on its payment entry.','Configured metadata is shown; Report CNIC takes precedence over existing CNIC. Bill-only tax is not automatically assigned to the payment. Missing metadata stays blank; any operational gap is logged.'),
])
add('Required Finance confirmation', 'Heading1')
add('Balance formula and deduction-source rule approved: Yes / No', 'Callout')
add('Reviewer / date: __________________  Exception references: __________________')

report_page(9,'Sales Tax Annexure Report',REPORTS[4][2], 'Supplier NTN/CNIC/type/province; bill identifiers/date; HS code/purchase type/rates; quantity/UOM; purchase base; sales tax, noncreditable input, extra tax, FED, ST withholding; deduction document/date and PRT type.')
cases([
 ('ANN-01','Bill, refund and numeric totals','Use a posted bill base 1,000 + sales tax 150 and a posted credit note base 200 + tax 30 in April.','Two document rows; bill +1,000/+150, credit note −200/−30; grand totals base 800 and tax 120. Totals agree with posted company-currency ledger amounts.'),
 ('ANN-02','Document grain and multiple taxes','Use a bill with multiple invoice lines and more than one tax. Compare source records and generated rows.','One row per bill/credit note. Tax names are listed together; base is not repeated per tax or rate. Client confirms this granularity meets the summary requirement.'),
 ('ANN-03','Date basis and supplier filters','Use a bill with invoice date 31-Mar and accounting date 01-Apr. Run March and April; test supplier/journal filters and a draft bill.','Bill is selected in April, while Document Date shows 31-Mar. Filters apply and draft bill is excluded. Company-currency values reconcile without a second conversion.'),
 ('ANN-04','Tax columns and supplier/bill metadata','Populate approved categories and the partner/AP Report Details fields; compare each applicable tax amount and classification.','Each category maps to its intended posted amount. Tax ID supplies NTN. CNIC, supplier type/province, HS, purchase/PRT and deduction metadata agree with records; no invented values.'),
 ('ANN-05','Quantity, UOM and blank data','Compare bills with a common UOM, mixed UOMs, a refund and incomplete metadata.','Common-UOM quantities are summed; refund quantity reverses sign. Mixed-UOM quantity is blank and UOM shows Mixed. Missing optional metadata stays blank and is identified for completion.'),
])

report_page(10,'Supplier Balances',REPORTS[5][2], 'Supplier code/reference and name; opening balance; period debit/credit; closing balance with Dr/Cr signs; grand totals; optional zero-balance suppliers.')
cases([
 ('SUP-01','Opening, movements and closing','Use opening payable 1,000 Cr at 31-Mar, April payments/debits 300 and bills/credits 500. Run April.','Opening = 1,000 Cr; Debit = 300; Credit = 500; Closing = 1,200 Cr. Signed equation: −1,000 + 300 − 500 = −1,200.'),
 ('SUP-02','Debit and zero-balance suppliers','Use an unmatched supplier advance of 250 and a supplier with no balance or period activity. Run with Include Suppliers with Zero Balances off/on.','Advance appears as 250 Dr. An inactive-zero supplier is added when zero inclusion is enabled. Suppliers with nonzero period turnover remain visible even when closing is zero.'),
 ('SUP-03','Boundary dates, filters and state','Identify movements before start, on both endpoints and after end, including a draft entry. Apply supplier/payable-account/journal filters.','Before-start entries affect opening; both endpoints affect period movement; after-end and draft entries are excluded. Supplier references and selected scope are correct.'),
 ('SUP-04','Ledger and aging agreement','Reconcile supplier detail and grand totals to posted payable ledger for the same scope; compare closing to Age Analysis at the same cutoff.','Opening plus debit minus credit equals closing for every supplier and total. Closing agrees to aging after sign translation; differences are documented and resolved.'),
])
add('Reconciliation evidence reference: _________________________________________________')
add('Finance reviewer / date: __________________________________________________________')

report_page(11,'Transaction List',REPORTS[6][2], 'Month/journal/date/voucher groups; creator and posted/draft state; account codes/descriptions; narration/reference; debit/credit; voucher, date, journal, month and grand totals.')
cases([
 ('TRN-01','Posted versus draft selection','Use a posted voucher debit/credit 100 and a draft voucher debit/credit 20. Run Posted Entries, then Draft and Posted Entries.','Posted totals = 100 debit and 100 credit. Draft-and-posted totals = 120 debit and 120 credit, with correct visible voucher states.'),
 ('TRN-02','Hierarchy and subtotals','Use several vouchers spanning two journals, days and months; run a range that includes them.','Entries group by month, journal, date and voucher. Each subtotal equals its included detail, and grand totals agree to the selected ledger scope without duplication.'),
 ('TRN-03','Voucher traceability','Select a voucher and compare line dates, account codes/names, sequence, narration, reference, creator and state.','Displayed values trace to source entries. Debit and credit agree exactly. With no line-level filters, each complete balanced voucher has equal debit and credit.'),
 ('TRN-04','Partial-voucher filtering and export','Apply an account or partner filter that selects one side of a balanced voucher; also test journal/date boundaries. Export PDF and CSV.','Only matching lines appear. Filtered totals may be unequal because a partial voucher is shown; the report does not add balancing lines. Scope and values match preview and exports.'),
])
add('Additional client-specific scenario / evidence: ________________________________________')
add('_____________________________________________________________________________')

page('12  Execution summary and exit criteria', 'Complete after execution and retesting; results remain pending until the client records them')
grid(['Test group','Cases','Pass','Fail','Blocked','N/A'],
     [('Common (per-report evidence)', '8','','','',''),('Age Analysis ACP','5','','','',''),
      ('Cost Centre-wise Income','4','','','',''),('Payments (All)','4','','','',''),
      ('Payments (Taxes)','4','','','',''),('Sales Tax Annexure','5','','','',''),
      ('Supplier Balances','4','','','',''),('Transaction List','4','','','',''),
      ('TOTAL distinct test cases','38','','','','')],(4100,1200,1200,1200,1200,1200))
add('Count each distinct case once. A common case passes only when all applicable reports pass it; retain the per-report results as evidence. List additional scenarios in the attached execution register.', 'Small')
add('Acceptance criteria', 'Heading1')
add('• All 38 cases are executed, or an N/A reason is approved by the client UAT lead. Blocked cases remain open; they are not treated as passes.')
add('• No open Critical or High defects. Any remaining Medium/Low issue has a documented impact, owner, target date and explicit client acceptance.')
add('• Financial figures reconcile to the approved source dataset. Unexplained monetary differences are not accepted. Approved rounding tolerance, if any: __________; otherwise no unexplained variance.')
add('• Business rules BR-01 to BR-09, tax mappings, annexure granularity and the available filters/layouts are accepted or have a resolved change request.')
add('• Evidence is complete; PDF/CSV checks pass; access restrictions and representative-volume response times meet client expectations.')
add('• Finance owner and authorised client approver complete the final sign-off. Conditional acceptance identifies each condition and its closure criteria.')
grid(['Completion control','Client entry'],[
 ('Executed by / reviewed by','____________________________________________'),
 ('Evidence pack location','____________________________________________'),
 ('Outstanding defect / exception IDs','____________________________________________'),
 ('Exit criteria satisfied','Yes / No / Conditional — explanation: __________________'),
])

page('13  Defects, exceptions and retest log', 'Use one detailed record per issue; duplicate this page or attach an issue register as needed')
grid(['Field','Issue record'],[
 ('Defect / exception ID','____________________________________________'),
 ('Report / test ID / release','____________________________________________'),
 ('Reported by / date','____________________________________________'),
 ('Severity / status','Critical / High / Medium / Low\nOpen / In progress / Ready for retest / Closed / Accepted exception'),
 ('Steps / filters / source IDs','________________________________________________________\n________________________________________________________'),
 ('Expected result','________________________________________________________\n________________________________________________________'),
 ('Actual result / business impact','________________________________________________________\n________________________________________________________'),
 ('Evidence reference','____________________________________________'),
 ('Owner / target date / resolution','________________________________________________________\n________________________________________________________'),
 ('Retest release / tester / date','____________________________________________'),
 ('Retest result / evidence','Pass / Fail / Blocked: _____________________________________'),
 ('Accepted exception / condition','Impact and agreed workaround: _____________________________\nClosure criterion / due date: _________________________________'),
 ('Client exception approval','Name: __________________  Signature/date: __________________'),
])
add('Severity guide', 'Heading1')
add('Critical: unauthorised data exposure or material widespread financial misstatement. High: key report unavailable or materially incorrect with no acceptable workaround. Medium: limited functional issue with an agreed workaround. Low: cosmetic or minor usability issue without monetary impact.', 'Small')
add('All open issues, including exceptions, must be referenced on the sign-off page. A signature does not automatically close an unresolved defect.', 'Small')

page('14  Client acceptance and sign-off', 'Document OPTIX-UAT-ACC-001 · Version 1.0 · Seven Accounting reports')
grid(['Acceptance baseline','Details to complete'],[
 ('Client / project','________________________________________________________'),
 ('Environment / database / company','________________________________________________________'),
 ('Accepted release / commit','________________________________________________________'),
 ('UAT execution / review dates','________________________________________________________'),
 ('Evidence pack / defect register','________________________________________________________'),
])
add('Client decision — select one', 'Heading1')
add('[ ] ACCEPTED — The scoped reports meet the agreed acceptance criteria.')
add('[ ] ACCEPTED WITH CONDITIONS — Only the documented conditions below remain; the client accepts their stated impact and closure plan.')
add('[ ] NOT ACCEPTED — The listed defects or unmet criteria require resolution and retesting.')
add('Conditions / excluded items / defect IDs / owner / due date:', 'Heading2')
add('_____________________________________________________________________________')
add('_____________________________________________________________________________')
add('Acceptance statement', 'Heading1')
add('We confirm that the UAT results and supporting evidence for the seven reports listed in this document have been reviewed. Our decision applies to the stated environment, release, scope, business rules and explicitly recorded exceptions. Blank or unexecuted results are not deemed accepted. Any outstanding condition remains subject to its agreed closure criteria.')
grid(['Role','Name / designation','Signature','Date'],[
 ('Client Finance owner',['',''],['',''],['','']),
 ('Client UAT lead',['',''],['',''],['','']),
 ('Authorised client approver',['',''],['',''],['','']),
 ('Implementation representative',['',''],['',''],['','']),
],(2400,3100,2900,1700))
add('Production / release authorisation', 'Heading2')
add('UAT acceptance and release authorisation are recorded separately. Deployment/continued use authorised: [ ] Yes  [ ] No  [ ] Not applicable', 'Small')
add('Authorised by: __________________  Effective date: __________________  Reference: __________________', 'Small')

assert len(pages) == 15
assert len(all_cases) == 38 and len(set(all_cases)) == 38

styles = f'''<w:styles xmlns:w="{NS}">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="20"/><w:color w:val="203040"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="110" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="130"/></w:pPr><w:rPr><w:b/><w:sz w:val="34"/><w:color w:val="123B5D"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:pPr><w:keepNext/><w:spacing w:after="190"/></w:pPr><w:rPr><w:sz w:val="21"/><w:color w:val="567185"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:keepNext/><w:spacing w:before="180" w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="25"/><w:color w:val="123B5D"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:pPr><w:keepNext/><w:spacing w:before="100" w:after="80"/></w:pPr><w:rPr><w:b/><w:sz w:val="21"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Cell"><w:name w:val="Table text"/><w:pPr><w:spacing w:after="65" w:line="225" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Small"><w:name w:val="Small"/><w:pPr><w:spacing w:after="100"/></w:pPr><w:rPr><w:sz w:val="18"/><w:color w:val="506272"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Callout"><w:name w:val="Callout"/><w:pPr><w:shd w:fill="E8EFF5"/><w:spacing w:before="150" w:after="150"/></w:pPr><w:rPr><w:b/><w:sz w:val="20"/></w:rPr></w:style>
</w:styles>'''
header = f'<w:hdr xmlns:w="{NS}">' + p('OPTIX  /  ACCOUNTING REPORTS                                           USER ACCEPTANCE TESTING', 'Small') + '</w:hdr>'
footer = f'''<w:ftr xmlns:w="{NS}"><w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="16"/><w:color w:val="506272"/></w:rPr><w:t xml:space="preserve">OPTIX-UAT-ACC-001 | v1.0 | Confidential     •     Page </w:t></w:r><w:fldSimple w:instr="PAGE"/><w:r><w:t xml:space="preserve"> of </w:t></w:r><w:fldSimple w:instr="NUMPAGES"/></w:p></w:ftr>'''
section = '''<w:sectPr><w:headerReference w:type="default" r:id="rId2"/><w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1000" w:right="903" w:bottom="1000" w:left="903" w:header="380" w:footer="400"/></w:sectPr>'''
body = ''.join(pages)
document = f'<w:document xmlns:w="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>{body}{section}</w:body></w:document>'
types = '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>'''
rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{}</Relationships>'
relation = '<Relationship Id="{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{}" Target="{}"/>'
with ZipFile(OUT / (NAME + '.docx'), 'w', ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', types)
    z.writestr('_rels/.rels', rels.format(relation.format('rId1','officeDocument','word/document.xml')))
    z.writestr('word/document.xml', document)
    z.writestr('word/styles.xml', styles)
    z.writestr('word/header1.xml', header)
    z.writestr('word/footer1.xml', footer)
    z.writestr('word/_rels/document.xml.rels', rels.format(relation.format('rId1','styles','styles.xml') + relation.format('rId2','header','header1.xml') + relation.format('rId3','footer','footer1.xml')))
print(f'Created {NAME}.docx: {len(pages)} planned pages, {len(all_cases)} test cases')
