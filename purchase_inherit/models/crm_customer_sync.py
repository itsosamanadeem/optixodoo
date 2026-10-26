import logging

import requests

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


API_URL = 'https://crm.optix.pk/api/app/GetCustomersWithMrc'
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    optix_crm_customer_id = fields.Integer(copy=False, index=True, readonly=True)
    optix_crm_customer_code = fields.Char(copy=False, index=True, readonly=True)
    optix_crm_area = fields.Char(readonly=True)
    optix_crm_sub_area = fields.Char(readonly=True)
    optix_crm_mrc = fields.Float(string='CRM MRC', readonly=True)
    optix_crm_status = fields.Char(readonly=True)

    _crm_customer_unique = models.UniqueIndex(
        '(optix_crm_customer_id) WHERE optix_crm_customer_id > 0',
        'This CRM customer already exists.'
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    optix_crm_access_key = fields.Char(
        string='CRM access key', config_parameter='purchase_inherit.crm_access_key',
        groups='base.group_system',
    )


class CrmCustomerSync(models.Model):
    _name = 'optix.crm.customer.sync'
    _description = 'CRM customer synchronization'

    name = fields.Char(default='CRM customer sync', required=True)
    state = fields.Selection([
        ('idle', 'Not started'), ('running', 'Running'),
        ('done', 'Completed'), ('failed', 'Failed'),
    ], default='idle', required=True)
    next_page = fields.Integer(default=1)
    total_pages = fields.Integer(default=0)
    total = fields.Integer(default=0)
    processed = fields.Integer(default=0)
    created = fields.Integer(default=0)
    updated = fields.Integer(default=0)
    error = fields.Text()
    started_at = fields.Datetime()
    finished_at = fields.Datetime()

    def _lock(self):
        self.ensure_one()
        self.env.cr.execute(
            'SELECT id FROM optix_crm_customer_sync WHERE id = %s FOR UPDATE', [self.id]
        )
        self.invalidate_recordset()

    def _start(self):
        self._lock()
        if self.state == 'running':
            return
        if not self.env['ir.config_parameter'].sudo().get_param('purchase_inherit.crm_access_key'):
            raise UserError(_('Configure the CRM access key in Inventory Settings first.'))
        # A failed run resumes at the first uncommitted page.
        values = {'state': 'running', 'error': False, 'finished_at': False}
        if self.state != 'failed':
            values.update(next_page=1, total_pages=0, total=0, processed=0,
                          created=0, updated=0, started_at=fields.Datetime.now())
        self.write(values)
        self.env.ref('purchase_inherit.ir_cron_crm_customer_worker')._trigger()

    @api.model
    def _cron_start(self):
        if not self.env['ir.config_parameter'].sudo().get_param('purchase_inherit.crm_access_key'):
            return
        self.env.ref('purchase_inherit.crm_customer_sync')._start()

    @api.model
    def _cron_process(self):
        job = self.env.ref('purchase_inherit.crm_customer_sync')
        job._lock()
        if job.state != 'running':
            return
        try:
            with self.env.cr.savepoint():
                job._process_page()
        except Exception as exc:
            # Do not expose HTTP headers, credentials or customer data in errors.
            _logger.warning('CRM import failed at page %s (%s)', job.next_page, type(exc).__name__)
            job.invalidate_recordset()
            job.write({'state': 'failed', 'error': _(
                'Page %s could not be imported. Check API connectivity, credentials '
                'and customer data, then click Sync CRM Customers to retry.', job.next_page
            )})
        remaining = max(job.total_pages - job.next_page + 1, 1) if job.state == 'running' else 0
        self.env['ir.cron']._commit_progress(1, remaining=remaining)

    def _process_page(self):
        key = self.env['ir.config_parameter'].sudo().get_param('purchase_inherit.crm_access_key')
        if not key:
            raise UserError(_('The CRM access key is missing.'))
        response = requests.get(API_URL, headers={'x-access-key': key},
                                params={'pageNumber': self.next_page, 'pageSize': 200},
                                timeout=(10, 30))
        response.raise_for_status()
        payload = response.json()
        if payload['response']['responseCode'] != 0:
            raise ValueError('CRM rejected the request')
        result = payload['result']
        page, pages, total = result['PageNumber'], result['TotalPages'], result['TotalCount']
        rows = result['Customers']
        if (any(type(v) is not int for v in (page, pages, total))
                or page != self.next_page or not isinstance(rows, list)
                or total < 0 or pages < 0 or len(rows) > 200
                or (total > 0 and (pages < 1 or page > pages))):
            raise ValueError('Invalid CRM pagination')
        if not rows and total:
            raise ValueError('Unexpected empty CRM page')
        ids = [row['CustomerId'] for row in rows]
        if any(type(cid) is not int or cid <= 0 for cid in ids) or len(set(ids)) != len(ids):
            raise ValueError('Invalid or duplicate CRM IDs')
        partners = self.env['res.partner'].sudo().with_context(active_test=False)
        existing = {p.optix_crm_customer_id: p for p in partners.search([
            ('optix_crm_customer_id', 'in', ids)
        ])}
        new_values = []
        updated = 0
        for row in rows:
            if not isinstance(row.get('Name'), str) or not row['Name'].strip():
                raise ValueError('Customer name is missing')
            values = {
                'optix_crm_customer_id': row['CustomerId'],
                'optix_crm_customer_code': row.get('CustomerCode') or False,
                'name': row['Name'].strip(), 'cnic_number': row.get('Cnic') or False,
                'street': row.get('Address') or False, 'city': row.get('City') or False,
                'email': row.get('Email') or False, 'phone': row.get('Phone') or False,
                'optix_crm_area': row.get('Area') or False,
                'optix_crm_sub_area': row.get('SubArea') or False,
                'optix_crm_mrc': row.get('Mrc') or 0,
                'optix_crm_status': row.get('StatusName') or False,
            }
            partner = existing.get(row['CustomerId'])
            if partner:
                values['customer_rank'] = max(partner.customer_rank, 1)
                changes = {k: v for k, v in values.items() if partner[k] != v}
                if changes:
                    partner.write(changes)
                    updated += 1
            else:
                values['customer_rank'] = 1
                new_values.append(values)
        if new_values:
            partners.create(new_values)
        done = page >= pages
        self.write({'next_page': page + 1, 'total_pages': pages, 'total': total,
                    'processed': self.processed + len(rows),
                    'created': self.created + len(new_values), 'updated': self.updated + updated,
                    'state': 'done' if done else 'running',
                    'finished_at': fields.Datetime.now() if done else False})


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_sync_crm_customers(self):
        self.ensure_one()
        if not self.env.user.has_group('stock.group_stock_user'):
            raise AccessError(_('Only inventory users can synchronize customers.'))
        self.check_access('write')
        if self.picking_type_code != 'outgoing':
            raise UserError(_('Customer sync is available on delivery receipts.'))
        job = self.env.ref('purchase_inherit.crm_customer_sync').sudo()
        job._start()
        return {'type': 'ir.actions.client', 'tag': 'optix_crm_customer_sync',
                'name': _('Sync CRM Customers'),
                'params': {'job_id': job.id, 'picking_id': self.id}}
