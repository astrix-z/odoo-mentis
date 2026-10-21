from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError


class Task(models.Model):
    _inherit = 'project.task'

    mentis_outlet_id = fields.Many2one(
        'mentis.outlet', string='Outlet', index=True, tracking=True,
        compute='_compute_mentis_outlet_id', store=True, readonly=False, recursive=True)
    mentis_network_id = fields.Many2one(
        related='mentis_outlet_id.network_id', string='Network', store=True, index=True)
    project_mentis_queue = fields.Selection(related='project_id.mentis_queue')
    mentis_scope_network_ids = fields.Many2many(
        'mentis.network', 'project_task_mentis_scope_network_rel', 'task_id', 'network_id',
        string='Scope Networks', help='Networks this task covers; every active outlet of them gets a sub-task.')
    mentis_scope_outlet_ids = fields.Many2many(
        'mentis.outlet', 'project_task_mentis_scope_outlet_rel', 'task_id', 'outlet_id',
        string='Scope Outlets', help='Individual outlets this task covers in addition to the scope networks.')

    @api.depends('parent_id.mentis_outlet_id')
    def _compute_mentis_outlet_id(self):
        for task in self:
            if not task.mentis_outlet_id and task.parent_id:
                task.mentis_outlet_id = task.parent_id.mentis_outlet_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._mentis_assign_service_staff(vals)
        return super().create(vals_list)

    @api.model
    def _mentis_assign_service_staff(self, vals):
        """Assign a new service task to the on-duty user, or to the outlet's responsible staff.

        Applies only when nobody was chosen explicitly: no assignees, or only the creator
        pre-filled by the "My Tasks" action while the creator is not service staff.
        """
        project_id = vals.get('project_id', self.env.context.get('default_project_id'))
        outlet_id = vals.get('mentis_outlet_id', self.env.context.get('default_mentis_outlet_id'))
        if not project_id or not outlet_id or vals.get('parent_id'):
            return
        if self.env['project.project'].browse(project_id).sudo().mentis_queue != 'service':
            return
        if 'user_ids' in vals:
            requested = set(self._fields['user_ids'].convert_to_cache(vals['user_ids'], self))
        else:
            requested = set(self._fields['user_ids'].convert_to_cache(
                self.env.context.get('default_user_ids') or [], self))
        if requested and (requested != {self.env.uid} or self.env.user.has_group('mentis_task_access.group_service')):
            return
        assignees = self.env['mentis.service.duty']._get_on_duty_user() \
            or self.env['mentis.outlet'].browse(outlet_id).sudo().service_user_ids
        if assignees:
            vals['user_ids'] = [Command.set(assignees.ids)]

    def _mentis_scope_outlets(self):
        self.ensure_one()
        outlets = self.mentis_scope_outlet_ids | self.mentis_scope_network_ids.outlet_ids
        return outlets.filtered('active').sorted(lambda outlet: (outlet.network_id.name, outlet.name))

    def action_mentis_create_outlet_subtasks(self):
        """Create one unassigned sub-task per scope outlet that does not have one yet."""
        self.ensure_one()
        if not self.allow_subtasks:
            raise UserError(_('Enable sub-tasks for the project "%s" first.', self.project_id.display_name))
        covered = self.with_context(active_test=False).child_ids.mentis_outlet_id
        outlets = self._mentis_scope_outlets() - covered
        if not outlets:
            raise UserError(_('Every outlet in the scope already has a sub-task.'))
        self.with_context(default_project_id=self.project_id.id).create([{
            'name': '%s — %s' % (self.name, outlet.name),
            'parent_id': self.id,
            'display_project_id': self.project_id.id,
            'mentis_outlet_id': outlet.id,
            'description': self.description,
            'date_deadline': self.date_deadline,
            'tag_ids': [Command.set(self.tag_ids.ids)],
            'user_ids': [Command.clear()],
        } for outlet in outlets])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('%s sub-tasks created.', len(outlets)),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        message = super().message_post(**kwargs)
        # Mentioning someone must let them open the task: subscribe mentioned internal users.
        if kwargs.get('message_type') == 'comment' and kwargs.get('partner_ids'):
            partners = self.env['res.partner'].sudo().browse(kwargs['partner_ids']).exists()
            internal = partners.filtered(lambda partner: partner.user_ids.filtered(lambda user: not user.share))
            if internal:
                self.sudo().message_subscribe(partner_ids=internal.ids)
        return message
