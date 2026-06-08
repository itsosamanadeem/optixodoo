# Odoo Apps Publishing Notes

## Recommended app name

`Purchase Control Hub`

This name fits Odoo's 25-character guideline and reflects the wider scope of the module better than a pure approval-only title.

## Technical name

`purchase_inherit`

## Suggested short summary

`Approvals, budgets, serial import, and master-data controls.`

## Suggested full description

Purchase Control Hub extends Odoo purchasing with stronger governance across purchase requests, approvals, budgets, analytics, serial tracking, and master data. It is built for companies that want tighter department-level procurement control from request submission to final receipt.

### Key features

- Department-based purchase request approvals
- Purchase order approval chain with sent-back review handling
- Budget restrict, warning, and allow rules
- Automatic analytic distribution from department settings
- Smart RFQ and purchase order creation from approved request lines
- Department manager activity notifications
- XLSX serial import for stock operations
- Auto-generated product and vendor codes
- Product warranty, asset tag, and vendor CNIC fields

## Suggested screenshot list

Use real Odoo UI screenshots in this order:

1. Approval request form with department lines and analytic distribution
2. Purchase order form with department managers and manager approval tags
3. Budget warning popup or budget restriction validation
4. Stock move operation with `Import Serials XLSX`
5. Product form with warranty and asset tag fields
6. Vendor form with generated code and CNIC field

## Store assets prepared

- `static/description/index.html` created for the Odoo Apps description page
- `static/description/banner.svg` created as a cover visual
- `static/description/workflow.svg` created as a process visual
- `README.rst` aligned with the app-store positioning
- `__manifest__.py` updated with a stronger publish name, summary, support email, and version

## Final publish checklist

- Replace or supplement the SVG visuals with real UI screenshots if possible
- Keep the module ZIP limited to the `purchase_inherit` folder
- Confirm all dependent modules are available for the target customer environment
- Review the current author and maintainer fields before public upload
