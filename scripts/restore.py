#!/usr/bin/env python3
"""Restore a snapshot into a NEW local mentis_dev database and neutralize it."""
from pathlib import Path
import os
import secrets
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
BACKUP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path((ROOT / '.local/latest-backup').read_text().strip())
COMPOSE = ['docker', 'compose']


def run(args, **kwargs):
    return subprocess.run(COMPOSE + args, check=True, **kwargs)


for filename in ('database.dump', 'filestore.tar.gz', 'source.tar.gz', 'inventory.json'):
    if not (BACKUP / filename).is_file():
        raise SystemExit(f'Missing snapshot file: {BACKUP / filename}')
if not (ROOT / '.env').exists() or not (ROOT / '.local/odoo.conf').exists():
    raise SystemExit('Create .env and .local/odoo.conf as described in README.md first.')
run(['up', '-d', '--wait', 'db'])
exists = run(['exec', '-T', 'db', 'psql', '-U', 'odoo', '-d', 'postgres', '-tAc',
              "SELECT 1 FROM pg_database WHERE datname='mentis_dev'"], capture_output=True, text=True).stdout.strip()
if exists:
    raise SystemExit('mentis_dev already exists; refusing to overwrite local development data.')
run(['stop', 'odoo'])
print('Extracting production source...', flush=True)
with tarfile.open(BACKUP / 'source.tar.gz') as archive:
    archive.extractall(ROOT / 'source', filter='data')
if (BACKUP / 'addons.tar.gz').exists():
    with tarfile.open(BACKUP / 'addons.tar.gz') as archive:
        archive.extractall(ROOT, filter='data')
run(['exec', '-T', 'db', 'createdb', '-U', 'odoo', '-O', 'odoo', 'mentis_dev'])
with (BACKUP / 'database.dump').open('rb') as dump:
    run(['exec', '-T', 'db', 'pg_restore', '-U', 'odoo', '-d', 'mentis_dev', '--no-owner', '--no-acl', '--exit-on-error'], stdin=dump)
with (BACKUP / 'filestore.tar.gz').open('rb') as store:
    run(['run', '--rm', '-T', '--no-deps', '--user', 'root', '--entrypoint', 'bash', 'odoo', '-ec',
         'mkdir -p /var/lib/odoo/filestore/mentis_dev; tar -xzf - -C /var/lib/odoo/filestore/mentis_dev; chown -R odoo:odoo /var/lib/odoo'], stdin=store)
run(['run', '--rm', '-T', '--no-deps', 'odoo', 'odoo', 'neutralize', '-c', '/etc/odoo/odoo.conf', '-d', 'mentis_dev'])
password = secrets.token_urlsafe(24)
credentials = ROOT / '.local/credentials.txt'
with open(credentials, 'w', opener=lambda p, flags: os.open(p, flags, 0o600)) as output:
    output.write(f'URL: http://localhost:8069\nDatabase: mentis_dev\nLogin: localadmin\nPassword: {password}\n')
with (ROOT / 'scripts/prepare_local.py').open('rb') as script:
    run(['run', '--rm', '-T', '--no-deps', '-e', 'LOCAL_ADMIN_PASSWORD', 'odoo', 'odoo', 'shell', '-c', '/etc/odoo/odoo.conf', '-d', 'mentis_dev', '--no-http'],
        stdin=script, env={**os.environ, 'LOCAL_ADMIN_PASSWORD': password})
run(['up', '-d', '--wait', '--wait-timeout', '180', 'web'])
print('Local instance started: http://localhost:8069; credentials: .local/credentials.txt')
