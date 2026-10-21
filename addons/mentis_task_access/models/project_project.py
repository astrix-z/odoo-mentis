from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = 'project.project'

    privacy_visibility = fields.Selection(default='followers')
    mentis_queue = fields.Selection(
        [('it', 'IT'), ('service', 'Service'), ('accounting', 'Accounting')],
        string='Department Queue',
        help='Department whose staff see the tasks of this project. '
             'Outlet and network roles see tasks of their outlets in any queue.')

    @api.constrains('mentis_queue', 'privacy_visibility')
    def _check_mentis_queue_visibility(self):
        if any(project.mentis_queue and project.privacy_visibility != 'followers' for project in self):
            raise ValidationError(_(
                'A department queue project must be visible to invited internal users only; '
                'other visibility settings expose its tasks to every employee.'))
