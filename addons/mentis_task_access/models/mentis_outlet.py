from odoo import fields, models


class MentisOutlet(models.Model):
    _name = 'mentis.outlet'
    _description = 'Outlet'
    _order = 'network_id, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    network_id = fields.Many2one('mentis.network', string='Network', required=True, ondelete='restrict')
    manager_ids = fields.Many2many(
        'res.users', 'mentis_outlet_manager_rel', 'outlet_id', 'user_id',
        string='Outlet Managers', domain=[('share', '=', False)])
    service_user_ids = fields.Many2many(
        'res.users', 'mentis_outlet_service_user_rel', 'outlet_id', 'user_id',
        string='Responsible Service Staff', domain=[('share', '=', False)],
        help='Service staff who handle this outlet on regular days. '
             'New service tasks of the outlet are assigned to them outside duty shifts.')
    accounting_user_ids = fields.Many2many(
        'res.users', 'mentis_outlet_accounting_user_rel', 'outlet_id', 'user_id',
        string='Accountants', domain=[('share', '=', False)],
        help='Accountants who see the accounting tasks of this outlet.')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Outlet code must be unique.'),
    ]
