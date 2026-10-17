#!/usr/bin/env python3
"""Smoke checks for restored data, local login, assets and network isolation."""
from pathlib import Path
import datetime
import http.cookiejar
import json
import os
import re
import subprocess
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)


def compose(*args, **kwargs):
    return subprocess.run(['docker', 'compose', *args], check=True, capture_output=True, text=True, **kwargs).stdout


def query(sql):
    result = compose('exec', '-T', 'db', 'psql', '-U', 'odoo', '-d', 'mentis_dev', '-tAc', sql)
    return json.loads(result)


state = query("""SELECT json_build_object(
 'crons_active', (SELECT count(*) FROM ir_cron WHERE active),
 'smtp_active', (SELECT count(*) FROM ir_mail_server WHERE active),
 'fetchmail_active', (SELECT count(*) FROM fetchmail_server WHERE active),
 'outgoing_mail', (SELECT count(*) FROM mail_mail WHERE state='outgoing'),
 'payment_active', (SELECT count(*) FROM payment_provider WHERE state != 'disabled'),
 'installed_modules', (SELECT count(*) FROM ir_module_module WHERE state='installed'),
 'base_url', (SELECT value FROM ir_config_parameter WHERE key='web.base.url'),
 'neutralized', (SELECT value FROM ir_config_parameter WHERE key='database.is_neutralized'))""")
for key in ('crons_active', 'smtp_active', 'fetchmail_active', 'outgoing_mail', 'payment_active'):
    assert state[key] == 0, (key, state[key])
assert state['neutralized'].lower() == 'true', state
assert state['base_url'] == 'http://localhost:8069', state
backup = Path((ROOT / '.local/latest-backup').read_text().strip())
inventory = json.loads((backup / 'inventory.json').read_text())
assert state['installed_modules'] == len(inventory['modules']), state
files = query("SELECT COALESCE(json_agg(store_fname), '[]'::json) FROM ir_attachment WHERE store_fname IS NOT NULL")
file_check = compose('exec', '-T', 'odoo', 'python3', '-c',
    "import sys,json,pathlib; files=json.load(sys.stdin); missing=[f for f in files if not (pathlib.Path('/var/lib/odoo/filestore/mentis_dev')/f).is_file()]; print(json.dumps({'attachments_checked':len(files),'missing':len(missing)})); sys.exit(bool(missing))",
    input=json.dumps(files))
state.update(json.loads(file_check))
credentials = dict(line.split(': ', 1) for line in (ROOT / '.local/credentials.txt').read_text().splitlines())
base = 'http://localhost:8069'
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
request = urllib.request.Request(base + '/web/session/authenticate', data=json.dumps({
    'jsonrpc': '2.0', 'method': 'call', 'params': {'db': 'mentis_dev', 'login': credentials['Login'], 'password': credentials['Password']}, 'id': 1,
}).encode(), headers={'Content-Type': 'application/json'})
with opener.open(request, timeout=60) as response:
    auth = json.load(response)
assert auth.get('result', {}).get('uid'), 'Local login failed'
state['login_ok'] = True
for path in ('/web', '/'):
    with opener.open(base + path, timeout=120) as response:
        html = response.read().decode()
        assert response.status == 200
        assert urllib.parse.urlparse(response.url).hostname in ('localhost', '127.0.0.1')
        assets = list(dict.fromkeys(re.findall(r'(?:src|href)="(/web/assets/[^"?]+)', html)))
        assert assets, f'No web assets on {path}'
        for asset in assets:
            with opener.open(base + asset.replace('&amp;', '&'), timeout=120) as content:
                assert content.status == 200 and content.read(), asset
        state['website_ok' if path == '/' else 'backend_ok'] = True
        state['website_assets' if path == '/' else 'backend_assets'] = len(assets)
container_id = compose('ps', '-q', 'odoo').strip()
network_id = json.loads(subprocess.check_output(
    ['docker', 'inspect', container_id], text=True))[0]['NetworkSettings']['Networks']
for network in network_id.values():
    info = json.loads(subprocess.check_output(['docker', 'network', 'inspect', network['NetworkID']], text=True))[0]
    assert info['Internal'], 'Odoo has an external Docker network'
compose('exec', '-T', 'odoo', 'python3', '-c',
    "import socket,sys\nfor host in ('1.1.1.1', '192.168.55.70'):\n try:\n  s=socket.create_connection((host,443),timeout=3)\n except OSError:\n  print('Outbound connection blocked:', host)\n else:\n  s.close(); sys.exit('Unexpected outbound access')")
state['outbound_blocked'] = True
state['verified_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(ROOT / '.local/verification.json').write_text(json.dumps(state, indent=2)+'\n')
print(json.dumps(state, indent=2))
