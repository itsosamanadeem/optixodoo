# About
============
`jl_list_advance_search_inventory` is the **inventory enhancement module** for Advanced List Search in Odoo.  
It extends the base `jl_list_advance_search` module for **inventory-related list views**, adding advanced column-header filters for faster operations without replacing Odoo native search.  
This module is designed to work together with Odoo Search Bar and Group By.

> **Important:** This module is not standalone.  
> Install `jl_list_advance_search` first, then use this module for inventory-specific compatibility.

# Module Type
============
1) **Module Name:** `jl_list_advance_search_inventory`
2) **Purpose:** Domain enhancement / Inventory list-view compatibility
3) **Functional Behavior:** Adds advanced list-header filters for supported inventory views
4) **Target Users:** Inventory users, warehouse staff, consultants, implementers, Odoo partners
5) **Release Type:** Free module (with paid dependency guidance)

# Purchase Guide
============
For best results, guide users to purchase the following modules:

1) **Base Core Module (Required)**
    - `jl_list_advance_search`
    - Link: https://apps.odoo.com/apps/modules/19.0/jl_list_advance_search/

2) **All-in-One Enhancement Package (Recommended)**
    - `jl_list_advance_search_package`
    - Link: https://apps.odoo.com/apps/modules/19.0/jl_list_advance_search_package/

# Core Features
============
1) **Inventory List Header Filters**
    - Adds filter inputs under column headers for inventory-related list views.

2) **Quick Trigger Search**
    - Search can trigger on Enter key or input blur for faster operations.

3) **Multi-Column Filtering**
    - Apply filters on multiple columns at the same time.

4) **Range-Based Conditions**
    - Date/Datetime and Numeric fields support From/To filtering.

5) **Compatible with Native Search & Group By**
    - Works with Odoo native search flow, not a replacement.

6) **Supports Inventory-Specific Components**
    - Helps inventory list renderers work with advanced filter widgets such as datetime picker and multi-record selector.

# Compatibility Scope
============
- ✅ Directly supported: inventory-related list views
- ⚠ Partially/conditionally supported: custom inventory list renderers
- ✅ Requires paid base module:
    - `jl_list_advance_search`
- ✅ Recommended paid package:
    - `jl_list_advance_search_package`
- ✅ Related enhancement modules:
    - `jl_list_advance_search_purchase`
    - `jl_list_advance_search_sales`
    - `jl_list_advance_search_expense`
    - `jl_list_advance_search_account`
    - `jl_list_advance_search_project`
    - `jl_list_advance_search_timesheet_grid`

# Installation
============
### Steps:
1) **Purchase & Install Base Module First**
    - Purchase and install `jl_list_advance_search`.

2) **(Optional) Purchase Package Module**
    - Purchase `jl_list_advance_search_package` if you need cross-domain compatibility quickly.

3) **Copy This Free Module**
    - Copy `jl_list_advance_search_inventory` into your Odoo addons path.

4) **Restart Odoo Service**
    - Restart Odoo service to reload modules.

5) **Update Apps List**
    - Enable developer mode and update Apps List.

6) **Install the Module**
    - Install `jl_list_advance_search_inventory`.

# Usage Instructions
============
After installation:
1) Open an inventory-related list view.
2) Use the advanced filter row under column headers.
3) Filter by field type (text / relation / selection / date range / numeric range).
4) Combine with native Search Bar and Group By for analysis.
5) Use reset action to clear all header filters quickly.

# Troubleshooting
============
1) **“Filter row not shown in some inventory views”**
    - Confirm `jl_list_advance_search` is installed and enabled.
    - Check whether the view uses a custom inventory renderer.
    - First, confirm the user has **enabled** advanced list search in user preferences.

2) **“Date or relation filter does not work”**
    - Upgrade both base and inventory modules.
    - Restart Odoo and clear browser cache.

3) **“Installed free module but feature incomplete”**
    - This is expected if base core module is missing.
    - Purchase/install `jl_list_advance_search`.
    - For broader app coverage, purchase/install `jl_list_advance_search_package`.

# Support Team
=====================================
E-Mail: odooprovider@163.com  
Website: https://www.odooprovider.cn