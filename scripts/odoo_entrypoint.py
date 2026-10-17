#!/usr/bin/env python3
"""Launch Odoo from this checkout, using host-provided dependencies/configuration."""
from pathlib import Path
import os
import sys

os.environ['TZ'] = 'UTC'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import odoo

if __name__ == '__main__':
    odoo.cli.main()
