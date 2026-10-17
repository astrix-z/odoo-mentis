# Git branches and production deployment

The shared bare repository is `jb@192.168.55.70:/home/jb/repos/odoo-mentis.git`.
The local checkout normally uses `developement` (spelling intentional). `stage` is
an integration branch; `production` contains reviewed production releases. These
are Git branches, not three running environments; no staging Odoo service is created.

The repository includes `source/odoo/`, custom `addons/`, local development tooling,
and production service scripts. Databases, filestore, `.env` and `.local/` stay
outside Git. Host dependencies and `/etc/odoo/odoo.conf` remain server-specific.

## Initial server cutover (root required)

A checkout on branch `production` is staged at `/home/jb/odoo-mentis`.
From an administrative console on the Odoo server, run:

```sh
bash /home/jb/odoo-mentis/deploy/install-production.sh
```

The script moves the checkout to `/srv/odoo-mentis`, verifies every source file
against the currently installed package, and installs a systemd override. Odoo
continues to run as user `odoo` with the existing database, filestore, configuration,
ports and logging. Both repository addon directories are enabled. No module upgrade
or database restore is performed. The service restarts briefly; a failed initial
health check restores the original service command. The original installed Python
package remains available for rollback. Effective service configuration and the
commit are recorded in `/var/backups/odoo-mentis/`.

Until that root script succeeds, the service still uses the system-installed code.
Inspect the active configuration with `systemctl cat odoo` and `systemctl show odoo -p ExecStart`.

## Branch workflow

Develop and verify changes locally, commit on `developement`, then promote:

```sh
git push origin developement
git switch stage
git merge --ff-only developement
git push origin stage
git switch production
git merge --ff-only stage
git push origin production
git switch developement
```

The server rejects non-fast-forward pushes and branch deletion. Pushing does not
restart Odoo or deploy automatically. From the server's administrative console:

```sh
bash /srv/odoo-mentis/deploy/update-production.sh
```

This requires a clean `production` checkout, fetches the shared repository, applies
a fast-forward update, restarts Odoo and checks `/web/login`. Review module/schema
changes separately and take a fresh database/filestore backup before any required
module upgrade. A failed update health check reports the previous commit; it does
not automatically roll back the database or rewrite Git history. Roll back code
through a reviewed revert on `production`, push, and deploy again.

Configure your own Git author name/email in each development checkout. The initial
local baseline uses repository-local author `jb <jb@localhost>`.
