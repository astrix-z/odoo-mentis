#!/usr/bin/env python3
"""Check initial repository baseline against the installed production package."""
from pathlib import Path
import hashlib
import sys

checkout = Path(__file__).resolve().parents[1] / 'source/odoo'
installed = Path('/usr/lib/python3/dist-packages/odoo')


def inventory(root):
    return {str(p.relative_to(root)): p for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').digest()


original, copy = inventory(installed), inventory(checkout)
missing = sorted(original.keys() - copy.keys())
extra = sorted(copy.keys() - original.keys())
changed = sorted(name for name in original.keys() & copy.keys() if digest(original[name]) != digest(copy[name]))
if missing or extra or changed:
    print('Production source mismatch:', {'missing': missing[:20], 'extra': extra[:20], 'changed': changed[:20]})
    sys.exit(1)
print(f'Production source matches repository: {len(original)} files.')
