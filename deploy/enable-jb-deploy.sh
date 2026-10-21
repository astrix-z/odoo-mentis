#!/bin/bash
# One-time permission setup; does not restart Odoo.
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Run this setup script as root.' >&2; exit 1; }
command -v pkaction >/dev/null || {
    echo 'Install polkit first: apt-get update && apt-get install -y polkitd' >&2
    exit 1
}
pkaction --action-id org.freedesktop.systemd1.manage-units >/dev/null
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install -d -o root -g root -m 755 /etc/polkit-1/rules.d
install -o root -g root -m 644 "$script_dir/50-odoo-mentis-deploy.rules" \
    /etc/polkit-1/rules.d/50-odoo-mentis-deploy.rules
echo 'jb can now restart odoo.service. Run update-production.sh as jb.'
