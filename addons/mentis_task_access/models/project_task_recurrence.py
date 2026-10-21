from odoo import api, models


class ProjectTaskRecurrence(models.Model):
    _inherit = 'project.task.recurrence'

    @api.model
    def _get_recurring_fields(self):
        return super()._get_recurring_fields() + [
            'mentis_outlet_id', 'mentis_scope_network_ids', 'mentis_scope_outlet_ids']

    def _new_task_values(self, task):
        values = super()._new_task_values(task)
        if task.parent_id and task.mentis_outlet_id:
            # Outlet sub-tasks start unassigned in every occurrence; IT distributes them again.
            values['user_ids'] = []
        return values
