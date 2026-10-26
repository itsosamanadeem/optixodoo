# Odoo Apps Publishing Notes

## Recommended app name

`Purchase Approval Flow`

This stays within Odoo's 25-character app name guideline and clearly describes the module.

## Technical name

`ml_purchase_approval`

## Suggested short summary

`Multi-step purchase order approval with amount-based levels.`

## Suggested store description

Purchase Approval Flow adds a structured approval workflow to Odoo purchase orders. Companies can define approval groups, assign users to each level, configure amount thresholds, and keep a complete history of recommendations, approvals, and returns.

### Key features

- Create approval groups for different purchase policies
- Define multiple approval levels with minimum and maximum amounts
- Support recommendation and approval stages in the same flow
- Assign responsible users to each approval level
- Show action buttons only to authorized users
- Record comments, actions, and timestamps in approval history
- Return purchase orders for correction when needed
- Integrate directly with the standard Odoo purchase order workflow

## Screenshot order

1. `static/description/assets/screenshots/2_screenshot.png`
   Purchase order screen with approval group, current level, and pending approver.
2. `static/description/assets/screenshots/1.png`
   Approval group setup with levels and amount ranges.
3. `static/description/assets/screenshots/3.png`
   Recommendation and return actions on the purchase order.
4. `static/description/assets/screenshots/4.png`
   Comment popup for recommendation or return.
5. `static/description/assets/screenshots/5.png`
   Approval history with actions, notes, and timestamps.
6. `static/description/assets/screenshots/6.png`
   Final approval button for the authorized user.

## Files prepared for publishing

- `__manifest__.py` updated with a store-safe name, semantic version, support email, and screenshot list.
- `static/description/index.html` rewritten as an Odoo Apps description page without external scripts.
- `README.rst` aligned with the published app positioning.

## Final check before upload

- Confirm the screenshots do not include any sensitive customer data.
- Zip only the `ml_purchase_approval` module folder for upload.
- Make sure your repository tag or upload version matches `19.0.1.0.0`.
