"""Complete the supplied SDD while preserving its images, relationships and layout."""
from pathlib import Path
from copy import deepcopy
import re
import zipfile
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/home/osama-nadeem/Downloads/Odoo_SCM_Finance_Updated_with_Optix_Customizations.docx')
OUTPUT = Path(__file__).parent / 'Odoo_SCM_Finance_Completed_Optix_v1.1.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
def tag(t): return '{%s}%s' % (W, t)
def text(n): return ''.join(n.itertext()).strip()
def p(s, style=None):
    n = E.Element(tag('p'))
    if style:
        E.SubElement(E.SubElement(n, tag('pPr')), tag('pStyle'), {tag('val'): style})
    E.SubElement(E.SubElement(n, tag('r')), tag('t')).text = s
    return n
def replace(n, s):
    props = n.find('w:pPr', NS)
    for c in list(n):
        if c is not props: n.remove(c)
    E.SubElement(E.SubElement(n, tag('r')), tag('t')).text = s
def table(rows):
    t = E.Element(tag('tbl'))
    pr = E.SubElement(t, tag('tblPr'))
    E.SubElement(pr, tag('tblStyle'), {tag('val'): 'TableGrid'})
    E.SubElement(pr, tag('tblW'), {tag('w'): '8900', tag('type'): 'dxa'})
    grid = E.SubElement(t, tag('tblGrid'))
    for _ in rows[0]: E.SubElement(grid, tag('gridCol'), {tag('w'): str(8900//len(rows[0]))})
    for i, row in enumerate(rows):
        tr = E.SubElement(t, tag('tr'))
        trpr = E.SubElement(tr, tag('trPr'))
        E.SubElement(trpr, tag('cantSplit'))
        if i == 0: E.SubElement(trpr, tag('tblHeader'))
        for value in row:
            tc = E.SubElement(tr, tag('tc'))
            tcpr = E.SubElement(tc, tag('tcPr'))
            E.SubElement(tcpr, tag('tcW'), {tag('w'): str(8900//len(row)), tag('type'): 'dxa'})
            if i == 0: E.SubElement(tcpr, tag('shd'), {tag('fill'): 'D9E2F3'})
            tc.append(p(value))
    return t

with zipfile.ZipFile(SOURCE) as z:
    data = {i.filename: z.read(i.filename) for i in z.infolist()}
# Retain namespace prefixes used by compatibility attributes and drawings.
for _, pair in E.iterparse(SOURCE.open('rb') if False else __import__('io').BytesIO(data['word/document.xml']), events=['start-ns']):
    prefix, uri = pair
    if not re.fullmatch(r'ns\d+', prefix): E.register_namespace(prefix, uri)
doc = E.fromstring(data['word/document.xml'])
body = doc.find('w:body', NS)
original = list(body)

setups = {
94: [('Field','Value / completion responsibility'), ('Company Name','OPTIX (Pvt.) Ltd — legal spelling to be verified by Finance'), ('Registered address','Pending Finance confirmation; no approved address supplied'), ('NTN / tax registration','Pending Finance confirmation; use approved registration certificate'), ('Operating address / branches','Pending SCM/Finance confirmation; distinguish from registered address'), ('Point of contact','Pending nomination: SCM process owner and Finance configuration owner')],
96: [('Setup item','Configuration / status'), ('Warehouse master','SCM to confirm actual warehouse names, company, short codes and addresses; no live master export supplied'), ('Receipt operation','Configure incoming operation and vendor/source and receiving/destination locations for each warehouse'), ('Receipt steps','SCM to approve one-, two- or three-step receiving; inspection requires an agreed controlled route'), ('Ownership / access','Assign responsible warehouse users and verify their company/location access')],
98: [('Setup item','Configuration / status'), ('Sub-inventory mapping','Represent storage areas as internal stock locations under the relevant warehouse; actual names pending SCM'), ('Department stores','Department Location (hr.department.location_id) supplies the destination for custom Internal Requests'), ('Quarantine / rejected area','Proposed controlled locations; SCM/Quality to approve disposition and access before use'), ('Availability','Location usage and routes determine availability; a location name alone does not enforce inspection holds')],
100: [('Location / usage','Design and outstanding decision'), ('Vendor / customer','Use appropriate external location usage; verify operation defaults'), ('Receiving / stock','Internal locations under each warehouse; actual hierarchy and codes pending SCM'), ('Department destination','Link each requesting department to its authorized internal destination'), ('Inspection / scrap / transit','Configure relevant usage and routes; approve quarantine release, scrap and inter-warehouse handling')],
103: [('Category / field','Required definition'), ('Goods / services','SCM to provide category hierarchy; goods tracking and services procurement differ'), ('Costing / valuation','Finance to approve methods and Odoo 19 accounting treatment per category; repository does not establish production values'), ('Accounting mapping','Finance to supply expense, valuation and applicable clearing accounts; product analytic GL is a separate analytic dimension'), ('Tracking / warranty','Product-level serial tracking where required; custom warranty duration is in days')],
105: [('UoM setup','Rule / owner'), ('Base / purchase UoM','SCM to confirm unit names for each item and its purchase unit'), ('Conversions','Configure conversions within the same UoM category; verify vendor pack sizes'), ('Quantity precision','Approve rounding for indivisible goods, lengths and services'), ('Serial-tracked goods','Verify individual serial assignments and quantities before transfer validation')],
107: [('Sequence','Repository definition / decision'), ('Contact code','res.partner.code: PART/ + five digits; supplied default, live next number unverified'), ('Product reference','product.template.sequence: PROD/ + five digits when internal reference is absent'), ('RFQ number','purchase.rfq: RFQ + five digits; confirmation can assign standard purchase.order sequence'), ('Other document numbering','PR, project, receipt, bill and payment sequences: verify installed application/company setup; prefixes not established here')],
109: [('Transaction','Implemented flow / setup'), ('Purchase Request / Project PR','Approvals-based request; approved eligible lines generate vendor purchasing documents'), ('Internal Request','Approved eligible goods lines create department internal transfers; configure destinations'), ('Revenue Share Request','Type and flag exist; confirm live purchasing entry point because current button visibility excludes this type'), ('Receipt / delivery / return','Use configured Inventory operations and standard return links; warehouse routes and tolerances require SCM approval')],
114: [('Payment-term item','Configuration / status'), ('Supplier defaults','Finance to provide approved terms per supplier; no production terms supplied'), ('Due dates / installments','Configure actual days, percentages and installment rules in Accounting'), ('PO and bill review','Review carried terms and maturity dates before confirmation/posting'), ('Settlement','Custom gross payment less WHT/STSP determines net payment; early-payment-discount write-offs are outside this custom flow')],
116: [('Tax setup','Configuration / status'), ('Bill taxes','Finance to approve rates, applicability, price inclusion, fiscal positions and accounts; no statutory rates inferred'), ('Payment WHT / STSP','Set Payment Deduction Category and Payment Deduction Account on eligible deduction taxes'), ('Report classification','Set Accounting Report Tax Category on corresponding ledger accounts; complete partner/bill/payment metadata'), ('Validation','Prevent double deduction of bill taxes; 5.5% in the guide is an illustration and is not an approved tax rate')],
}
for idx, rows in setups.items():
    at = list(body).index(original[idx]); body.remove(original[idx]); body.insert(at, table(rows))

replacements = {
92: 'The following setup register records repository-supported behavior and required configuration. Pending values require the named business owner because no approved company master-data export or live database was supplied. Proposed controls are not evidence of deployed enforcement.',
224: 'Optix implements requisitions through Approvals renamed Purchase Request, extended by purchase_inherit and project_pr_budget. Department managers are added on submission; eligible non-refused lines can proceed after full or partial approval.',
244: 'If refused, departmental lines retain refusal user/date and the request may be partially approved. Use the permitted withdrawal/reset and resubmission process for corrections; refusal does not itself establish an automatic return-to-draft workflow.',
286: 'Create a project and enter Project Products with planned quantity, UoM and estimated unit cost. Task Creation, Area Creation, Inventory Creation and Civil Work are business examples; a dedicated project-type selector is not established by this repository.',
290: 'Project PR validation checks the approved project, company, planned products, committed quantity and remaining amount. No separate Project Team/Budget workflow queue is established by this extension.',
337: 'At PO confirmation, the customization checks analytic city/GL setup and a matching confirmed analytic budget. Finance configures Restrict, Allow or Show only warning.',
339: 'Restrict blocks a line exceeding its matching budget amount. Show only warning provides Proceed/Cancel; Allow permits exceeding that amount after required setup checks. This check compares individual line subtotals and does not aggregate overall PO or historical spend.',
340: 'Project PR separately checks committed request quantity and amount against the approved project plan. Community budgets are a third, separate budget model.',
383: 'Enter actual quantities and handle backorders under the configured operation. Receipt tolerances and over-receipt blocking must be verified in the deployed system; no custom tolerance engine is established by the reviewed addons.',
415: 'Finance records and resolves mismatches before posting/payment under an approved operating procedure. Automatic invoice holds, routing and tolerance enforcement require confirmation in the deployed system.',
444: 'Accounting design requires Finance validation on the deployed Odoo 19 configuration. Do not assume every goods receipt posts a journal entry. Verify valuation records and any accounting entry for the chosen category and valuation mode; where a receipt entry applies, the illustrative direction is debit inventory and credit stock input/clearing.',
447: 'Posting a vendor bill credits Accounts Payable and debits the configured expense, inventory or clearing account plus applicable recoverable taxes. Exact accounts and timing depend on the installed Odoo 19 accounting setup; validate with a representative receipt/bill/return scenario.',
450: 'Illustrative custom supplier settlement: gross 100,000, WHT 5,500 and net 94,500. Debit Accounts Payable 100,000; credit WHT payable 5,500; credit bank/outstanding payments 94,500. Bank reconciliation clears outstanding payments as configured. The percentage is an example, not a prescribed tax rate.',
520: 'This revised reference restores the complete customization coverage, including seven Optix accounting reports, cost centre expenses and role/setup responsibilities. Descriptions are based on repository source and existing technical documentation; installation and live configuration remain to be verified.',
}
for idx, value in replacements.items(): replace(original[idx], value)
replace(original[2], 'OPTIX (Pvt.) Ltd | Odoo 19 | SCM & Finance | End-to-End Procure-to-Stock Process & Customizations | Version 1.1 | 16 October 2026 | Draft for Business Review')
for n in original[37].iter(tag('t')):
    if n.text == '1.0': n.text = '1.1'
    elif n.text == 'Initial design': n.text = 'Completed setup register and customization coverage; 16 October 2026'
# Resolve duplicate subsection numbering without changing existing bookmark targets.
replace(original[118], '6.11 Vendor / Supplier Master')
for idx in [123,128,133,138,143,148,153,158]:
    replace(original[idx], re.sub(r'^6\.(\d+)', lambda m: '6.'+str(int(m[1])+1), text(original[idx])))
replace(original[281], '8.2.1 Project Purchase Requisition (PR) Process')

# Replace incomplete Part II body using the full existing source guide.
end = original[-1] if original[-1].tag == tag('sectPr') else None
for n in original[521:]:
    if n is not end and n in list(body): body.remove(n)
guide = (ROOT/'docs/customization/Optix_Complete_Customization_Guide.md').read_text()
lines = guide.splitlines(); i = 0; additions = []
while i < len(lines):
    s = lines[i]
    if s.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            cells=[c.strip() for c in lines[i].strip('|').split('|')]
            if not all(re.fullmatch(r'[-: ]+',c) for c in cells): rows.append(cells)
            i+=1
        additions.append(table(rows)); continue
    if s.startswith('# '): pass
    elif s.startswith('## '): additions.append(p(s[3:], 'Heading1'))
    elif s.startswith('### '): additions.append(p(s[4:], 'Heading2'))
    elif s: additions.append(p(s))
    i+=1
additions[0] = p('Customization reference | Revision 1.1 | 16 October 2026 | Repository review; live configuration unverified')
additions += [p('15. Outstanding decisions and acceptance evidence', 'Heading1'), p('The following items require business data or deployment evidence. They are not confirmed custom implementations.'), table([
('Item / owner','Required completion or acceptance evidence'),
('Company and sites / Finance, SCM','Legal address, NTN, named contacts, warehouse/location hierarchy, product categories and approved UoM list'),
('Approvals / SCM, Finance','Named level users and limits; confirm sequence behavior and test unauthorized actions, refusal, partial approval and Return PR'),
('Receiving and quality / SCM, Quality','Approve receipt steps, tolerances and quarantine release; verify Quality availability, control points and blocking behavior'),
('Vendor restrictions / SCM','Approve activation policy and verify enforcement; no custom approved/blocked supplier workflow is demonstrated here'),
('Invoice matching / Finance','Approve tolerance and hold procedure; demonstrate enforcement before describing automatic holds as implemented'),
('Valuation / Finance','Approve category accounts and costing; retain actual Odoo 19 receipt, bill, return and payment journal evidence'),
('Budget controls / Finance','Test missing analytic setup and all three confirmation modes; verify project quantity/amount limits separately'),
('Payments and reports / Finance','Test full/partial/grouped payments, deductions, advice references and all report exports against ledger totals'),
('Inventory extensions / SCM, IT','Validate extra-row XLSX import compatibility, standard lot assignment and warranty expiry refresh requirement'),
('Deployment / IT','Confirm installed modules, analytic fields x_plan6_id/x_plan8_id, user visibility, CRM schedule and backup restore evidence'),
('Final sign-off / process owners','Record actual names, dates, decisions and UAT evidence; signatures cannot be completed from repository data')]), p('16. Revision record and source traceability', 'Heading1'), p('Revision 1.1 fills ten setup tables, corrects duplicated section numbering, integrates current request/project/budget behavior, qualifies unverified controls and accounting assumptions, and restores full report/access documentation. Original images and package relationships are retained. Source document remains unchanged.'), p('Evidence: purchase_inherit/data/*sequence.xml; purchase_inherit/models/hr_department.py, purchase_order.py, approval_request.py, account_payment.py; purchase_inherit/wizard/stock_serial_import_wizard.py; project_pr_budget/models/approval_request.py and project_project.py; fw_account_reports/README.md; cost_center_expense_report/README.md; docs/customization/Optix_Complete_Customization_Guide.md. Existing guide source references identify the remaining addon definitions. No application behavior or production data was changed.')]
pos = list(body).index(end) if end is not None else len(body)
for n in additions: body.insert(pos,n); pos+=1
data['word/document.xml'] = E.tostring(doc, encoding='utf-8', xml_declaration=True)
if 'word/settings.xml' in data:
    settings=E.fromstring(data['word/settings.xml'])
    update=settings.find('w:updateFields',NS)
    if update is None: update=E.SubElement(settings,tag('updateFields'))
    update.set(tag('val'),'true')
    data['word/settings.xml']=E.tostring(settings,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(OUTPUT,'w',zipfile.ZIP_DEFLATED) as z:
    for name, content in data.items(): z.writestr(name, content)
with zipfile.ZipFile(OUTPUT) as z:
    assert z.testzip() is None
    for name in z.namelist():
        if name.endswith('.xml'): E.fromstring(z.read(name))
    assert {n for n in z.namelist() if n.startswith('word/media/')} == {n for n in data if n.startswith('word/media/')}
print(OUTPUT)
