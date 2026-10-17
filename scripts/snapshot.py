#!/usr/bin/env python3
"""Read-only production snapshot over SSH; credentials stay on the server."""
import datetime
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / '.local/backups' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
BACKUP.mkdir(parents=True, mode=0o700)
HOST = 'jb@192.168.55.70'
REMOTE_SOURCE = '''from pathlib import Path
import subprocess, sys
command = subprocess.check_output(['systemctl', 'show', 'odoo', '-p', 'ExecStart', '--value'], text=True)
managed = '/srv/odoo-mentis/scripts/odoo_entrypoint.py' in command
active_source = Path('/srv/odoo-mentis/source/odoo' if managed else '/usr/lib/python3/dist-packages/odoo')
sys.path.insert(0, str(active_source.parent))
'''


def remote(script, target):
    with target.open('xb') as output:
        subprocess.run(['ssh', '-o', 'BatchMode=yes', HOST, 'python3 -'], input=(REMOTE_SOURCE + script).encode(), stdout=output, check=True)


remote('''import configparser, json, odoo.release, psycopg2
c=configparser.ConfigParser(); c.read('/etc/odoo/odoo.conf'); o=c['options']
cn=psycopg2.connect(host=o['db_host'],user=o['db_user'],password=o['db_password'],dbname=o['db_name'])
cn.set_session(readonly=True)
with cn.cursor() as q:
 q.execute("SELECT name, latest_version FROM ir_module_module WHERE state='installed' ORDER BY name")
 modules=q.fetchall()
print(json.dumps(dict(odoo_version=odoo.release.version, database=o['db_name'], modules=modules),indent=2))
''', BACKUP / 'inventory.json')
print('Exporting database...', flush=True)
remote('''import configparser, os
c=configparser.ConfigParser(); c.read('/etc/odoo/odoo.conf'); o=c['options']
os.environ['PGPASSWORD']=o['db_password']
os.execvp('pg_dump',['pg_dump','-h',o['db_host'],'-U',o['db_user'],'-Fc','--no-owner','--no-acl',o['db_name']])
''', BACKUP / 'database.dump')
print('Copying filestore...', flush=True)
remote('''import configparser, os
c=configparser.ConfigParser(); c.read('/etc/odoo/odoo.conf'); o=c['options']
os.execvp('tar',['tar','-czf','-','-C',o['data_dir']+'/filestore/'+o['db_name'],'.'])
''', BACKUP / 'filestore.tar.gz')
print('Copying active Odoo source...', flush=True)
remote('''import os
os.execvp('tar',['tar','--dereference','--exclude=__pycache__','--exclude=*.pyc','-czf','-','-C',str(active_source.parent),'odoo'])
''', BACKUP / 'source.tar.gz')
remote('''import tarfile
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz', dereference=True) as archive:
 if managed:
  archive.add('/srv/odoo-mentis/addons', arcname='addons', filter=lambda info: None if '__pycache__' in info.name or info.name.endswith('.pyc') else info)
''', BACKUP / 'addons.tar.gz')
(ROOT / '.local/latest-backup').write_text(str(BACKUP.relative_to(ROOT))+'\n')
print(f'Snapshot complete: {BACKUP}')
