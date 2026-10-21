# Git branches and production deployment

The shared private repository is https://github.com/astrix-z/odoo-mentis.
Local `origin` uses HTTPS with GitHub CLI authentication. The production checkout
uses SSH and a dedicated read-only deploy key stored only on the server.
The previous bare repository remains at `/home/jb/repos/odoo-mentis.git`; its local
remote is named `server`, and its server-checkout remote is named `server-backup`.
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

All production updates are performed by the agent, including delivering changed
deployment scripts, promoting the release, running deployment, and verifying the
result. Do not ask the user to execute routine update commands manually. The agent
connects as `jb`:

```sh
ssh jb@192.168.55.70 'bash /srv/odoo-mentis/deploy/update-production.sh'
```

Before deployment, inspect the server checkout and reconcile any server-only
commits through the shared repository. After deployment, verify the actual server
HEAD with `git -C /srv/odoo-mentis rev-parse HEAD`, service status, and HTTP health;
report the deployed commit and outcome. The script's printed target commit alone
does not establish the actual HEAD when the server has local commits. If SSH or
permissions prevent completion, report the concrete blocker. Root is reserved for
initial setup and operations that specifically require elevated privileges.

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

Use fast-forward promotion and avoid force pushes or deleting release branches.
GitHub branch protection is not configured. Pushing does not restart Odoo or deploy automatically. From the server SSH session as `jb` (after the one-time permission setup below):

```sh
bash /srv/odoo-mentis/deploy/update-production.sh
```

The script must run as `jb`, not root. This requires a clean `production` checkout, fetches the shared repository, applies
a fast-forward update, restarts Odoo and checks `/web/login`. Review module/schema
changes separately and take a fresh database/filestore backup before any required
module upgrade. A failed update health check reports the previous commit; it does
not automatically roll back the database or rewrite Git history. Roll back code
through a reviewed revert on `production`, push, and deploy again.

Configure your own Git author name/email in each development checkout. The initial
local baseline uses repository-local author `jb <jb@localhost>`.

The server repository config selects `/home/jb/.ssh/odoo-mentis-github_ed25519`
via `core.sshCommand`; the private key is not copied locally or committed. GitHub
host keys are pinned in `/home/jb/.ssh/odoo-mentis-github_known_hosts` using the
GitHub HTTPS metadata API. This deploy key permits fetches, not pushes.

## Allow deployment as jb (one-time root setup)

After these deployment files have been delivered to the server, run as root:

```sh
# Only if polkit is not installed:
apt-get update
apt-get install -y polkitd
bash /srv/odoo-mentis/deploy/enable-jb-deploy.sh
```

This installs a root-owned polkit rule permitting only user `jb` to restart
`odoo.service`. Polkit reloads rules automatically; setup does not restart Odoo.
No sudo installation or authentication agent is needed, including over SSH.
The initial cutover script still requires root.

For each subsequent deployment, the agent connects as `jb` and runs:

```sh
bash /srv/odoo-mentis/deploy/update-production.sh
```

Remove `/etc/polkit-1/rules.d/50-odoo-mentis-deploy.rules` as root to revoke
this permission. Ensure any server-only commits have been incorporated into
`origin/production` before deploying; the update must remain a fast-forward.

## Deployment script checks

Run from the repository root with Python 3 and Bash (no database, systemd or
network required; external commands are mocked):

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
bash -n deploy/update-production.sh deploy/enable-jb-deploy.sh
```

These checks do not exercise real server polkit authorization or restart Odoo.
