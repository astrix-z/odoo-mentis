# Repository Guidelines

## Production Updates

All production updates are performed by the agent. Carry out the complete update
workflow, including delivering deployment script changes, deploying, and verifying
the result; do not hand routine deployment commands to the user to execute.
Connect over SSH as `jb@192.168.55.70` and run
`bash /srv/odoo-mentis/deploy/update-production.sh` as `jb`. Polkit permits restarting
`odoo.service`; routine updates do not require root or sudo. Follow
`deploy/README.md` for branch promotion and deployment checks. Verify the actual
server Git HEAD and HTTP health after deployment and report the result.
If access or privileges block completion, report the specific blocker. Root is
required only for initial service/permission setup or changes requiring it.

## Project Structure & Module Organization

This repository tracks the production Odoo 16.0 instance (`odoo-host.pp.ua`) and the
tooling for a local Docker replica and production deployment. `README.md` (local
development, in Russian) and `deploy/README.md` (deployment) document the details.

- `source/odoo/`: exact copy of the Odoo package installed on production, including
  third-party modules. Production runs from this checkout, so every change here ships.
  Do not reformat or edit it casually.
- `addons/`: custom Odoo 16 addons, one directory per addon with its own
  `__manifest__.py`; organize models, views, security rules, and tests in their
  conventional subdirectories. Included in both local and production addon paths.
- `scripts/`: local setup (`init.py`), production snapshot (`snapshot.py`), restore
  and neutralization (`restore.py`, `prepare_local.py`), smoke checks (`verify.py`),
  and the production entrypoint (`odoo_entrypoint.py`).
- `deploy/`: production install/update scripts, systemd drop-in, and polkit rule.
- `config/`, `docker/`, `compose.yaml`: local Docker runtime (isolated network, Nginx
  front end, `config/odoo.conf.example` template).
- `tests/`: unittest checks for deployment scripts.
- `.local/` and `.env`: snapshots, credentials, and local configuration; gitignored.

## Build, Test, and Development Commands

Requires Python 3.12+ and Docker Engine with Compose. From the repository root:

```sh
docker compose up -d        # local instance at http://localhost:8069
python3 scripts/verify.py   # smoke checks of the restored environment
```

Initial replica: `python3 scripts/init.py`, `docker compose build odoo`,
`python3 scripts/snapshot.py`, `python3 scripts/restore.py`. Upgrade a module after
manifest, model, or schema changes:

```sh
docker compose stop odoo
docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d mentis_dev -u my_module --stop-after-init --no-http
docker compose up -d web
```

Record new tooling commands in `README.md`. No formatter or linter is configured.

## Coding Style & Naming Conventions

Use four spaces for Python indentation, `snake_case` for Python modules and functions, and `PascalCase` for classes. Use descriptive addon and file names. Keep changes focused and avoid unrelated formatting edits.

Add formatter or linter configuration alongside the code it governs, and document how to run it.

## Testing Guidelines

Add tests with new behavior and regression tests with bug fixes. For Python tests, use `test_*.py` filenames and descriptive `test_*` method names.

Deployment script checks (no server, database, or network needed; external commands are mocked):

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
bash -n deploy/update-production.sh deploy/enable-jb-deploy.sh
```

Run Odoo module tests with `--test-enable --test-tags /my_module --stop-after-init`
against a separate test database or Compose project, never `mentis_dev`.

## Commit & Pull Request Guidelines

Use concise, imperative commit subjects, such as `Add initial addon manifest`.
Commit on `developement`, then promote to `stage` and `production` by fast-forward
only, as described in `deploy/README.md`; never force-push or delete release branches.

Pull requests should explain the purpose, summarize behavior changes, link relevant issues, and state how changes were validated. Include screenshots for visible UI changes and setup notes for new dependencies.

## Security & Configuration

Never commit credentials, database dumps, or local secrets. Provide sanitized configuration examples and document required environment variables when configuration is introduced.
