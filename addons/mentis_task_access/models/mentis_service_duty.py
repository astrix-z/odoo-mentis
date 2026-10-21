from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MentisServiceDuty(models.Model):
    _name = 'mentis.service.duty'
    _description = 'Service Duty Shift'
    _order = 'date_start desc'

    user_id = fields.Many2one(
        'res.users', string='On Duty', required=True, ondelete='restrict',
        domain=lambda self: [('groups_id', 'in', self.env.ref('mentis_task_access.group_service').id)])
    date_start = fields.Datetime(string='Start', required=True)
    date_end = fields.Datetime(string='End', required=True)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if any(shift.date_end <= shift.date_start for shift in self):
            raise ValidationError(_('A duty shift must end after it starts.'))

    def name_get(self):
        return [(shift.id, '%s: %s – %s' % (shift.user_id.name, shift.date_start, shift.date_end)) for shift in self]

    @api.model
    def _get_on_duty_user(self, at=None):
        """Return the service user on duty at ``at`` (now by default), or an empty recordset."""
        at = at or fields.Datetime.now()
        shift = self.sudo().search(
            [('date_start', '<=', at), ('date_end', '>', at)],
            order='date_start desc, id desc', limit=1)
        return shift.user_id
