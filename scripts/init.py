#!/usr/bin/env python3
"""Create local configuration without replacing existing files."""
from pathlib import Path
import os
import secrets

root = Path(__file__).resolve().parents[1]
local = root / '.local'
local.mkdir(exist_ok=True, mode=0o700)
local.chmod(0o700)
for dirname in ('addons', 'source'):
    (root / dirname).mkdir(exist_ok=True)
files = {
    root / '.env': ('DB_PASSWORD=' + secrets.token_urlsafe(32) + '\n', 0o600),
    local / 'odoo.conf': ((root / 'config/odoo.conf.example').read_text().replace(
        'REPLACE_WITH_RANDOM_LOCAL_PASSWORD', secrets.token_urlsafe(32)), 0o644),
}
for path, (content, mode) in files.items():
    if path.exists():
        print(f'Keeping {path.relative_to(root)}')
        continue
    with open(path, 'x', opener=lambda p, flags: os.open(p, flags, mode)) as output:
        output.write(content)
    print(f'Created {path.relative_to(root)}')
