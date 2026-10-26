from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCrmCustomerSync(TransactionCase):
    def setUp(self):
        super().setUp()
        self.job = self.env.ref('purchase_inherit.crm_customer_sync')
        self.env['ir.config_parameter'].sudo().set_param('purchase_inherit.crm_access_key', 'test-key')
        self.row = {'CustomerId': 987654321, 'CustomerCode': 'CRM-TEST', 'Name': 'CRM test',
                    'Cnic': None, 'Phone': None, 'Email': None, 'City': 'Karachi', 'Mrc': 10}

    def response(self, rows, page=1, pages=1, total=None):
        return Mock(json=lambda: {'response': {'responseCode': 0}, 'result': {
            'Customers': rows, 'PageNumber': page, 'TotalPages': pages,
            'TotalCount': len(rows) if total is None else total}})

    def test_create_update_and_nulls(self):
        with patch('odoo.addons.purchase_inherit.models.crm_customer_sync.requests.get',
                   return_value=self.response([self.row])) as request:
            self.job._process_page()
            self.assertEqual(request.call_args.kwargs['params']['pageNumber'], 1)
        partner = self.env['res.partner'].search([('optix_crm_customer_id', '=', self.row['CustomerId'])])
        self.assertEqual(len(partner), 1)
        self.assertFalse(partner.cnic_number)
        self.assertEqual(partner.customer_rank, 1)
        code = partner.code
        self.row['Name'] = 'Updated CRM test'
        self.job.write({'next_page': 1})
        with patch('odoo.addons.purchase_inherit.models.crm_customer_sync.requests.get',
                   return_value=self.response([self.row])):
            self.job._process_page()
        self.assertEqual(partner.name, 'Updated CRM test')
        self.assertEqual(partner.code, code)
        self.assertEqual(self.job.created, 1)
        self.assertEqual(self.job.updated, 1)

    def test_failed_page_rolls_back_and_resumes(self):
        partner = self.env['res.partner'].create({
            'name': 'Original name', 'optix_crm_customer_id': self.row['CustomerId'],
        })
        self.job.write({'state': 'running'})
        bad = dict(self.row, CustomerId=987654322, Name='')
        with patch('odoo.addons.purchase_inherit.models.crm_customer_sync.requests.get',
                   return_value=self.response([self.row, bad])), \
                patch('odoo.addons.base.models.ir_cron.IrCron._commit_progress'):
            self.job._cron_process()
        self.assertEqual(self.job.state, 'failed')
        self.assertEqual(self.job.next_page, 1)
        self.assertEqual(partner.name, 'Original name')
        self.job._start()
        self.assertEqual(self.job.state, 'running')
        self.assertEqual(self.job.next_page, 1)

    def test_pagination_and_empty_database(self):
        with patch('odoo.addons.purchase_inherit.models.crm_customer_sync.requests.get',
                   return_value=self.response([self.row], pages=2, total=2)):
            self.job._process_page()
        self.assertEqual(self.job.state, 'running')
        self.assertEqual(self.job.next_page, 2)
        self.job.write({'next_page': 1, 'processed': 0})
        with patch('odoo.addons.purchase_inherit.models.crm_customer_sync.requests.get',
                   return_value=self.response([], pages=0)):
            self.job._process_page()
        self.assertEqual(self.job.state, 'done')

    def test_regular_partners_do_not_conflict(self):
        partners = self.env['res.partner'].create([{'name': 'Local one'}, {'name': 'Local two'}])
        self.assertEqual(len(partners), 2)

    def test_nightly_schedule(self):
        cron = self.env.ref('purchase_inherit.ir_cron_crm_customer_nightly')
        self.assertEqual(cron.nextcall.hour, 21)
        self.assertEqual(cron.nextcall.minute, 0)
        self.assertEqual(cron.interval_type, 'days')
        self.assertEqual(cron.interval_number, 1)

    def test_inventory_permissions_and_delivery_button(self):
        from odoo.exceptions import AccessError, UserError
        from odoo.tests.common import new_test_user
        user = new_test_user(self.env, login='crm_inventory_test', groups='stock.group_stock_user')
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
        })
        action = picking.with_user(user).action_sync_crm_customers()
        self.assertEqual(action['tag'], 'optix_crm_customer_sync')
        self.assertEqual(self.job.state, 'running')
        with self.assertRaises(AccessError):
            self.job.with_user(user).write({'state': 'done'})
        incoming = self.env['stock.picking.type'].search([('code', '=', 'incoming')], limit=1)
        picking.picking_type_id = incoming
        with self.assertRaises(UserError):
            picking.with_user(user).action_sync_crm_customers()
