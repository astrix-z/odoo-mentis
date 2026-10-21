# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Git-tracked copy of the production Odoo 16.0 instance `odoo-host.pp.ua` (server `jb@192.168.55.70`, PostgreSQL 15), plus tooling for a neutralized local Docker replica and for deploying to production. `README.md` (Russian) and `deploy/README.md` (English) are the authoritative docs; `AGENTS.md` holds the deployment rules below.

## Layout and how the pieces connect

- `source/odoo/` is an **exact copy of the Odoo package installed on the production server**, including third-party modules (~500 addons). Production runs from this directory. `scripts/check_production_source.py` hash-compares it against `/usr/lib/python3/dist-packages/odoo` during initial cutover. Don't edit or reformat it casually: every change ships to production.
- `addons/` is for custom addons (one directory per addon with `__manifest__.py`). It's empty so far. It's on the addons path both locally (`/mnt/extra-addons`) and in production (`/srv/odoo-mentis/addons`).
- **Local runtime** (`compose.yaml`): `db` (postgres) and `odoo` sit only on an `internal: true` network, so they have no outbound access. `web` (nginx, `config/nginx.conf`) bridges to `127.0.0.1:8069`. `source/odoo` is bind-mounted over the image's Odoo package, and Odoo runs with `--dev=reload,qweb,xml`. Config comes from `.local/odoo.conf`, generated from `config/odoo.conf.example` by `scripts/init.py`. `.env` holds `DB_PASSWORD`.
- **Production runtime**: systemd `odoo.service` with the drop-in `deploy/odoo-repository.conf` runs `scripts/odoo_entrypoint.py`. That script puts `source/` on `sys.path` and calls `odoo.cli.main()` from the checkout at `/srv/odoo-mentis` (branch `production`). The server keeps its own `/etc/odoo/odoo.conf`, database and filestore.
- `.local/` (snapshots, credentials, local config) and `.env` are gitignored and contain real production data or secrets. Never commit or publish them.

## Local environment commands

```sh
docker compose up -d                 # start (http://localhost:8069; creds in .local/credentials.txt, login localadmin)
docker compose logs -f odoo
python3 scripts/verify.py            # smoke checks -> .local/verification.json
```

First-time replica: `python3 scripts/init.py && docker compose build odoo && python3 scripts/snapshot.py && python3 scripts/restore.py`. `snapshot.py` is read-only against production over SSH. `restore.py` refuses to overwrite an existing `mentis_dev`, then runs `odoo neutralize` plus `scripts/prepare_local.py`, which disables crons and mail, rewrites website URLs and resets the admin.

After manifest, model or schema changes, upgrade the module:

```sh
docker compose stop odoo
docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d mentis_dev -u my_module --stop-after-init --no-http
docker compose up -d web
```

Run Odoo module tests with `--test-enable --test-tags /my_module --stop-after-init` against a **separate** test database or Compose project, not `mentis_dev`.

## Repository tests (deployment scripts)

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest tests.test_deployment.DeploymentTests.test_dirty_checkout_is_rejected_before_fetch_or_restart  # single test
bash -n deploy/update-production.sh deploy/enable-jb-deploy.sh
```

`tests/test_deployment.py` runs `deploy/update-production.sh` with mocked `id`/`git`/`systemctl`/`curl` placed on `PATH`. The tests don't need a server or network.

## Branches and production deployment

Branches: `developement` (note the spelling) → `stage` → `production`, promoted only by fast-forward (`git merge --ff-only`). Don't force-push or delete release branches. `origin` is the private GitHub repo. `server` is the legacy remote on the production host. Pushing doesn't deploy anything.

**The agent performs production deployments itself.** Don't hand routine deploy commands to the user. After promoting and pushing `production`:

```sh
ssh jb@192.168.55.70 'bash /srv/odoo-mentis/deploy/update-production.sh'
```

- Before deploying, inspect the server checkout for server-only commits and reconcile them through `origin`. The update must stay a fast-forward, and the script refuses a dirty checkout.
- The script must run as `jb`, not root. Polkit (`deploy/50-odoo-mentis-deploy.rules`, installed once by `deploy/enable-jb-deploy.sh`) lets `jb` restart `odoo.service`. Root is needed only for initial setup (`deploy/install-production.sh`) or similar privileged changes.
- The script doesn't run module upgrades or roll back the database. Review schema changes separately and take a database/filestore backup before any `-u`. To roll back code, push a reviewed revert on `production` and deploy again.
- Afterwards, verify the actual server HEAD (`git -C /srv/odoo-mentis rev-parse HEAD`), `systemctl` status and HTTP health (`/web/login`). Report the deployed commit and the outcome. The commit the script prints isn't proof on its own. If access or privileges block a step, report the specific blocker.
