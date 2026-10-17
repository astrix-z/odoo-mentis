#!/bin/bash
# One-time root installation. Does not change the database or odoo.conf.
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Run this script as root.' >&2; exit 1; }
repo=/srv/odoo-mentis
staged=/home/jb/odoo-mentis
dropin=/etc/systemd/system/odoo.service.d/odoo-repository.conf
[[ ! -e "$dropin" ]] || { echo 'Repository service override already exists; inspect it before reinstalling.' >&2; exit 1; }
if [[ ! -e "$repo" ]]; then
    [[ -d "$staged/.git" ]] || { echo 'Staged checkout not found.' >&2; exit 1; }
    mv "$staged" "$repo"
fi
[[ -d "$repo/.git" && ! -L "$repo" ]] || { echo 'Unexpected repository path.' >&2; exit 1; }
branch=$(runuser -u jb -- git -C "$repo" branch --show-current)
[[ "$branch" == production ]] || { echo 'Checkout must be on production.' >&2; exit 1; }
[[ -z $(runuser -u jb -- git -C "$repo" status --porcelain) ]] || { echo 'Checkout must be clean.' >&2; exit 1; }
# Initial cutover must use exactly the code already installed on this server.
runuser -u jb -- python3 "$repo/scripts/check_production_source.py"
runuser -u odoo -- /usr/bin/python3 "$repo/scripts/odoo_entrypoint.py" --version
backup=/var/backups/odoo-mentis/$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 700 "$backup"
systemctl cat odoo > "$backup/odoo.service.before.txt"
runuser -u jb -- git -C "$repo" rev-parse HEAD > "$backup/commit.txt"
install -d -m 755 "$(dirname "$dropin")"
install -m 644 "$repo/deploy/odoo-repository.conf" "$dropin"
rollback() {
    echo 'Cutover failed; restoring the original Odoo service command.' >&2
    rm -f "$dropin"
    systemctl daemon-reload
    systemctl restart odoo
}
trap rollback ERR
systemctl daemon-reload
systemctl restart odoo
healthy=false
for attempt in {1..20}; do
    if systemctl is-active --quiet odoo && curl -fsS --max-time 5 -o /dev/null http://127.0.0.1:8069/web/login; then
        healthy=true
        break
    fi
    sleep 2
done
[[ "$healthy" == true ]]
trap - ERR
echo "Odoo now runs from $repo on branch production. Service backup: $backup"
