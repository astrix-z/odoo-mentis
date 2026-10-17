# Repository Guidelines

## Project Structure & Module Organization

This workspace is currently empty: no application code, tests, assets, or build configuration has been committed. The directory name is `odoo-mentis`, but an Odoo version and module layout have not yet been established.

When introducing the initial implementation, document the actual directory layout in `README.md`. Keep related source, tests, and assets together, and avoid adding empty placeholder directories. For Odoo addons, use a dedicated directory per addon with its own `__manifest__.py`; organize models, views, security rules, and tests in their conventional subdirectories.

## Build, Test, and Development Commands

No build, test, lint, or local server commands are currently configured. Do not assume that `npm test`, `make`, or an Odoo executable is available.

When adding tooling, record exact setup and execution commands in `README.md`, including the supported runtime, dependency installation, database setup, and required configuration. Prefer reproducible commands that work from the repository root.

## Coding Style & Naming Conventions

Until project-specific tooling is introduced, use four spaces for Python indentation, `snake_case` for Python modules and functions, and `PascalCase` for classes. Use descriptive addon and file names. Keep changes focused and avoid unrelated formatting edits.

Add formatter or linter configuration alongside the code it governs, and document how to run it.

## Testing Guidelines

No testing framework or coverage threshold is configured. Add tests with new behavior and regression tests with bug fixes. For Python tests, use `test_*.py` filenames and descriptive `test_*` method names. Document the test runner and any required services before making tests mandatory.

## Commit & Pull Request Guidelines

There is no Git history from which to infer commit conventions. Use concise, imperative commit subjects, such as `Add initial addon manifest`.

Pull requests should explain the purpose, summarize behavior changes, link relevant issues, and state how changes were validated. Include screenshots for visible UI changes and setup notes for new dependencies.

## Security & Configuration

Never commit credentials, database dumps, or local secrets. Provide sanitized configuration examples and document required environment variables when configuration is introduced.
