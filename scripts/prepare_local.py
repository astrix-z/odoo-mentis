"""Executed inside `odoo shell` against mentis_dev only."""
import os

if env.cr.dbname != 'mentis_dev':
    raise RuntimeError('Refusing to prepare a database other than mentis_dev')
env['ir.cron'].search([]).write({'active': False})
env['ir.mail_server'].search([]).write({'active': False, 'smtp_pass': False, 'smtp_user': False})
env['fetchmail.server'].search([]).write({'active': False, 'password': False})
env['mail.mail'].search([('state', '=', 'outgoing')]).write({'state': 'cancel'})
params = env['ir.config_parameter'].sudo()
params.set_param('web.base.url', 'http://localhost:8069')
params.set_param('web.base.url.freeze', 'True')
params.set_param('database.is_neutralized', 'True')
for key in ('recaptcha_public_key', 'recaptcha_private_key'):
    params.set_param(key, '')
for index, website in enumerate(env['website'].search([], order='id')):
    hostname = 'localhost' if index == 0 else f'site-{website.id}.localhost'
    website.write({'domain': f'http://{hostname}:8069'})
admin = env.ref('base.user_admin')
admin.write({'login': 'localadmin', 'password': os.environ['LOCAL_ADMIN_PASSWORD'], 'email': 'localadmin@example.invalid'})
if 'totp_secret' in admin._fields:
    admin.write({'totp_secret': False})
params.set_param('database.uuid', __import__('uuid').uuid4().hex)
env.cr.commit()
print('Local database prepared; all cron jobs and mail servers disabled.')
