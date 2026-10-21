from odoo import fields, models


class MentisNetwork(models.Model):
    _name = 'mentis.network'
    _description = 'Retail Network'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    manager_ids = fields.Many2many(
        'res.users', 'mentis_network_manager_rel', 'network_id', 'user_id',
        string='Network Managers', domain=[('share', '=', False)])
    outlet_ids = fields.One2many('mentis.outlet', 'network_id', string='Outlets')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Network code must be unique.'),
    ]
