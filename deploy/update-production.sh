#!/bin/bash
# Explicit deployment after pushing production. No automatic database upgrades.
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Run this script as root.' >&2; exit 1; }
repo=/srv/odoo-mentis
as_jb() { runuser -u jb -- git -C "$repo" "$@"; }
[[ $(as_jb branch --show-current) == production ]]
[[ -z $(as_jb status --porcelain) ]] || { echo 'Checkout is dirty; refusing deployment.' >&2; exit 1; }
as_jb fetch origin production
previous=$(as_jb rev-parse HEAD)
next=$(as_jb rev-parse origin/production)
git_log=$(as_jb log --oneline "$previous..$next")
printf '%s\n' "$git_log"
as_jb merge --ff-only origin/production
systemctl restart odoo
for attempt in {1..20}; do
    if systemctl is-active --quiet odoo && curl -fsS --max-time 5 -o /dev/null http://127.0.0.1:8069/web/login; then
        echo "Deployed production: $next (previous: $previous)"
        exit 0
    fi
    sleep 2
done
echo "Health check failed. Inspect journalctl -u odoo; previous commit: $previous" >&2
exit 1
