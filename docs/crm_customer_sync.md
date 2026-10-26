# CRM customer synchronization

Upgrade `purchase_inherit` (Purchase Control Hub), restart the Odoo service, and
refresh the browser so the new backend assets load. In Inventory → Configuration
→ Settings → Optix CRM, an administrator must enter the API access key and save.
The key is held in `ir.config_parameter` and is never sent to the browser as part
of an API request. No credential is included in source code.

Open Inventory → Operations → Deliveries and open a receipt. Click **Sync CRM
Customers**. The form is saved before the background import starts. The progress
screen polls every three seconds; **Return to receipt** reopens the saved receipt
with an up-to-date customer selector. Leaving the screen does not cancel the job.
Clicking the button again displays the running job. A failed job resumes at its
first uncommitted page; a completed job starts a new full scan.

The nightly action starts a scan at 02:00 Asia/Karachi (21:00 UTC the preceding
day). The worker processes 200 customers per batch and commits progress using
Odoo 19's cron batching mechanism. A once-per-minute worker also picks up pending
work if a run times out. Cron workers must be enabled. Both scheduled actions
appear under Settings → Technical → Automation → Scheduled Actions.

`CustomerId` is the unique integration identity. CRM customer code is stored
separately from the existing Odoo partner sequence. Name, address, city, CNIC,
email, phone, area, subarea, MRC and status are updated from the CRM; null contact
values clear the corresponding imported value. Unchanged partners are not written.
CRM status is informational: it does not archive partners or affect transactions.
Customers missing from the API are not removed.

Existing Odoo contacts without a CRM ID are not automatically matched by name,
phone or CNIC. If such contacts already represent these CRM customers, link them
to their CRM IDs before the first import to avoid separate contact records. The
sync runs with elevated privileges and creates shared contacts; inventory users
can start the fixed integration and read progress, but cannot change its job or
credentials. There is one shared job per database to prevent overlapping imports.

The nightly scan reads all API pages, since this endpoint exposes no incremental
change filter in the supplied response. Duration depends on the CRM and database.

Tests in `purchase_inherit/tests/test_crm_customer_sync.py` mock API responses and
cover creation, updates, null fields, pagination, failure rollback and resume.
