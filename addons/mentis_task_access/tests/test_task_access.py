from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestTaskAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, mail_create_nolog=True, mail_notrack=True))

        def user(login, group):
            return new_test_user(cls.env, login=login, groups='base.group_user,mentis_task_access.%s' % group)

        cls.executive = user('exec', 'group_executive')
        cls.bufet_manager = user('bufet_manager', 'group_network_manager')
        cls.bufet1_manager = user('bufet1_manager', 'group_outlet_manager')
        cls.it_user = user('it_user', 'group_it')
        cls.service_bufet1 = user('service_bufet1', 'group_service')
        cls.service_goodtime1 = user('service_goodtime1', 'group_service')
        cls.accountant = user('accountant', 'group_accounting')
        cls.employee = new_test_user(cls.env, login='employee', groups='base.group_user,project.group_project_user')

        Network = cls.env['mentis.network']
        cls.bufet = bufet = Network.create({'name': 'Bufet', 'code': 'bufet', 'manager_ids': [(6, 0, cls.bufet_manager.ids)]})
        cls.goodtime = goodtime = Network.create({'name': 'Goodtime', 'code': 'goodtime'})
        Outlet = cls.env['mentis.outlet']
        cls.bufet1 = Outlet.create({
            'name': 'Bufet 1', 'code': 'bufet-01', 'network_id': bufet.id,
            'manager_ids': [(6, 0, cls.bufet1_manager.ids)],
            'service_user_ids': [(6, 0, cls.service_bufet1.ids)],
        })
        cls.bufet2 = Outlet.create({'name': 'Bufet 2', 'code': 'bufet-02', 'network_id': bufet.id})
        cls.goodtime1 = Outlet.create({
            'name': 'Goodtime 1', 'code': 'goodtime-01', 'network_id': goodtime.id,
            'service_user_ids': [(6, 0, cls.service_goodtime1.ids)],
        })

        Project = cls.env['project.project']
        cls.it = Project.create({'name': 'IT', 'mentis_queue': 'it', 'allow_subtasks': True, 'allow_recurring_tasks': True})
        cls.service = Project.create({'name': 'Service', 'mentis_queue': 'service'})
        cls.accounting = Project.create({'name': 'Accounting', 'mentis_queue': 'accounting'})

        def task(name, project, outlet=None):
            return cls.env['project.task'].create({
                'name': name, 'project_id': project.id,
                'mentis_outlet_id': outlet and outlet.id, 'user_ids': [(6, 0, [])],
            })

        cls.service_b1 = task('Service bufet-01', cls.service, cls.bufet1)
        cls.service_b2 = task('Service bufet-02', cls.service, cls.bufet2)
        cls.service_g1 = task('Service goodtime-01', cls.service, cls.goodtime1)
        cls.it_b1 = task('IT bufet-01', cls.it, cls.bufet1)
        cls.it_g1 = task('IT goodtime-01', cls.it, cls.goodtime1)
        cls.accounting_task = task('Close the month', cls.accounting)
        cls.all_tasks = cls.service_b1 | cls.service_b2 | cls.service_g1 | cls.it_b1 | cls.it_g1 | cls.accounting_task

    def visible(self, user):
        return self.env['project.task'].with_user(user).search([('id', 'in', self.all_tasks.ids)])

    def test_visibility_by_role(self):
        self.assertEqual(self.visible(self.executive), self.all_tasks)
        self.assertEqual(self.visible(self.bufet_manager), self.service_b1 | self.service_b2 | self.it_b1)
        self.assertEqual(self.visible(self.bufet1_manager), self.service_b1 | self.it_b1)
        self.assertEqual(self.visible(self.it_user), self.it_b1 | self.it_g1)
        self.assertEqual(self.visible(self.service_bufet1), self.service_b1)
        self.assertEqual(self.visible(self.service_goodtime1), self.service_g1)
        self.assertEqual(self.visible(self.accountant), self.accounting_task)
        self.assertFalse(self.visible(self.employee))

    def test_reassigning_outlet_moves_visibility(self):
        self.bufet1.manager_ids = [(6, 0, [])]
        self.assertFalse(self.visible(self.bufet1_manager))
        self.bufet2.manager_ids = [(6, 0, self.bufet1_manager.ids)]
        self.assertEqual(self.visible(self.bufet1_manager), self.service_b2)

    def test_access_error_outside_scope(self):
        with self.assertRaises(AccessError):
            self.service_g1.with_user(self.bufet1_manager).read(['name'])

    def test_assignee_and_follower_see_task(self):
        self.it_g1.user_ids = [(4, self.employee.id)]
        self.service_b2.message_subscribe(partner_ids=self.employee.partner_id.ids)
        self.assertEqual(self.visible(self.employee), self.it_g1 | self.service_b2)

    def test_mention_grants_access(self):
        self.it_b1.with_user(self.bufet1_manager).message_post(
            body='Please check', message_type='comment', partner_ids=self.employee.partner_id.ids)
        self.assertEqual(self.visible(self.employee), self.it_b1)

    def test_roles_see_queue_projects(self):
        projects = self.env['project.project'].with_user(self.bufet1_manager).search([])
        self.assertEqual(projects & (self.it | self.service | self.accounting), self.it | self.service | self.accounting)

    def test_outlet_manager_creates_service_task_for_responsible_staff(self):
        task = self.env['project.task'].with_user(self.bufet1_manager).with_context(
            default_user_ids=[(4, self.bufet1_manager.id)],  # what the "My Tasks" action pre-fills
        ).create({'name': 'Broken fryer', 'project_id': self.service.id, 'mentis_outlet_id': self.bufet1.id})
        self.assertEqual(task.user_ids, self.service_bufet1)
        self.assertIn(task, self.env['project.task'].with_user(self.bufet1_manager).search([]))

    def test_duty_shift_takes_new_service_tasks(self):
        now = fields.Datetime.now()
        self.env['mentis.service.duty'].create({
            'user_id': self.service_goodtime1.id,
            'date_start': now - timedelta(hours=1), 'date_end': now + timedelta(hours=1),
        })
        task = self.env['project.task'].with_user(self.bufet1_manager).create({
            'name': 'No power', 'project_id': self.service.id, 'mentis_outlet_id': self.bufet1.id})
        self.assertEqual(task.user_ids, self.service_goodtime1)
        self.assertIn(task, self.env['project.task'].with_user(self.service_goodtime1).search([]))

    def test_explicit_assignee_is_kept(self):
        task = self.env['project.task'].with_user(self.bufet1_manager).create({
            'name': 'Ask Goodtime', 'project_id': self.service.id, 'mentis_outlet_id': self.bufet1.id,
            'user_ids': [(6, 0, self.service_goodtime1.ids)]})
        self.assertEqual(task.user_ids, self.service_goodtime1)

    def test_non_service_queue_is_not_auto_assigned(self):
        # Created from the IT project's kanban, which passes default_project_id.
        task = self.env['project.task'].with_user(self.bufet1_manager).with_context(
            default_project_id=self.it.id,
        ).create({'name': 'Printer', 'mentis_outlet_id': self.bufet1.id})
        self.assertFalse(task.user_ids)

    def test_subtask_inherits_outlet(self):
        subtask = self.env['project.task'].create({
            'name': 'Order part', 'project_id': self.service.id, 'parent_id': self.service_b1.id})
        self.assertEqual(subtask.mentis_outlet_id, self.bufet1)
        self.assertIn(subtask, self.env['project.task'].with_user(self.bufet1_manager).search([]))

    def test_queue_project_must_be_invite_only(self):
        with self.assertRaises(ValidationError):
            self.it.privacy_visibility = 'employees'

    def test_task_analysis_follows_task_visibility(self):
        Report = self.env['report.project.task.user'].with_user(self.bufet1_manager)
        rows = Report.search([('task_id', 'in', self.all_tasks.ids)])
        self.assertEqual(rows.task_id, self.service_b1 | self.it_b1)

    def scoped_it_task(self, **vals):
        return self.env['project.task'].with_user(self.it_user).with_context(default_project_id=self.it.id).create({
            'name': 'Hardware maintenance', 'user_ids': [(6, 0, self.it_user.ids)], **vals})

    def test_network_manager_sees_task_scoped_to_network(self):
        bufet_wide = self.scoped_it_task(mentis_scope_network_ids=[(6, 0, self.bufet.ids)])
        goodtime_wide = self.scoped_it_task(mentis_scope_network_ids=[(6, 0, self.goodtime.ids)])
        bufet_outlet = self.scoped_it_task(mentis_scope_outlet_ids=[(6, 0, self.bufet2.ids)])
        visible = self.env['project.task'].with_user(self.bufet_manager).search([])
        self.assertIn(bufet_wide, visible)
        self.assertIn(bufet_outlet, visible)
        self.assertNotIn(goodtime_wide, visible)
        self.assertNotIn(bufet_wide, self.env['project.task'].with_user(self.bufet1_manager).search([]))

    def test_create_outlet_subtasks(self):
        parent = self.scoped_it_task(
            mentis_scope_network_ids=[(6, 0, self.bufet.ids)],
            mentis_scope_outlet_ids=[(6, 0, self.goodtime1.ids)])
        parent.action_mentis_create_outlet_subtasks()
        self.assertEqual(parent.child_ids.mentis_outlet_id, self.bufet1 | self.bufet2 | self.goodtime1)
        self.assertFalse(parent.child_ids.user_ids)
        self.assertEqual(parent.child_ids.project_id, self.it)

        own = parent.child_ids.filtered(lambda task: task.mentis_outlet_id == self.bufet1)
        visible = self.env['project.task'].with_user(self.bufet1_manager).search([('id', 'child_of', parent.id)])
        self.assertEqual(visible, own)

        with self.assertRaises(UserError):
            parent.action_mentis_create_outlet_subtasks()
        bufet3 = self.env['mentis.outlet'].create({'name': 'Bufet 3', 'code': 'bufet-03', 'network_id': self.bufet.id})
        parent.action_mentis_create_outlet_subtasks()
        self.assertEqual(len(parent.child_ids), 4)
        self.assertEqual(len(parent.child_ids.filtered(lambda task: task.mentis_outlet_id == bufet3)), 1)

    def test_archived_outlets_get_no_subtask(self):
        self.bufet2.active = False
        parent = self.scoped_it_task(mentis_scope_network_ids=[(6, 0, self.bufet.ids)])
        parent.action_mentis_create_outlet_subtasks()
        self.assertEqual(parent.child_ids.mentis_outlet_id, self.bufet1)

    def test_recurrence_keeps_outlets_and_clears_assignees(self):
        parent = self.scoped_it_task(
            mentis_scope_network_ids=[(6, 0, self.bufet.ids)],
            recurring_task=True, repeat_interval=3, repeat_unit='month', repeat_type='forever',
            repeat_on_month='date', repeat_day='1', repeat_week='first', repeat_weekday='mon')
        parent.action_mentis_create_outlet_subtasks()
        parent.child_ids.user_ids = [(6, 0, self.it_user.ids)]

        parent.recurrence_id._create_next_task()
        next_parent = parent.recurrence_id.task_ids - parent
        self.assertEqual(len(next_parent), 1)
        self.assertEqual(next_parent.mentis_scope_network_ids, self.bufet)
        self.assertEqual(next_parent.child_ids.mentis_outlet_id, self.bufet1 | self.bufet2)
        self.assertFalse(next_parent.child_ids.user_ids)
        self.assertIn(
            next_parent.child_ids.filtered(lambda task: task.mentis_outlet_id == self.bufet1),
            self.env['project.task'].with_user(self.bufet1_manager).search([]))
