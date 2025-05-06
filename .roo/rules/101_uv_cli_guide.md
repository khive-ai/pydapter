---
title: "uv Usage Guide"
by: "Ocean"
scope: "project"
created: "2025-05-05"
updated: "2025-05-05"
version: "1.0"
description: guide to using `uv` for managing virtual environments and dependencies
---

## 1. Why `uv`?

`uv` is a modern, extremely fast tool, aiming to replace `pip`, `venv`,
`virtualenv`. It is, significantly faster package installation and resolution
compared to `pip`. it handles environment creation, package installation,
locking, and syncing. `uv` uses `pyproject.toml` as the source of truth, and
modern packaging standards (PEP 517, PEP 621, etc.)

## 2. Core Workflows (CLI Commands)

> retain from using `uv pip install` directly:
>
> - if you want to add an dependency use `uv add`
> - to sync with `pyproject.toml` use `uv sync`

- `uv sync`, sync the environment to match pyproject.toml, you can do
  `uv sync --extra group` to also sync the optinal dependencies
- `uv run`, run a command in the environment, e.g. `uv run pytest tests/`,
  `uv run python src/my_script.py --arg1 value`
- `uv venv`, create a virtual environment in the current directory (then
  `source .venv/bin/activate`)
- `uv add xxx`, add a dependency to the project
- `uv add "xxx[extra1]"`, add a dependency with extras
- `uv remove xxx`, remove a dependency from the project
- `uv add --dev xxx`, add a development dependency
- `uv pip install -e .`, install the project in editable mode
- `uv build`, build the project
- `uv pip compile pyproject.toml -o requirements.lock` to generate a lock file
- `uv pip sync requirements.lock` to sync the environment to match the lock file
  exactly

**Note:**

- `uv pip xxx` does not alter the `pyproject.toml` file
- `uv run` automatically finds and uses the `.venv` in the current or parent
  directories. (so if you have multiple venv going on, navigate to the right
  directory before running `uv run`, don't really need to manually activate the
  venv)

## 3. Other Useful Commands

- `uv pip list`: List all installed packages in the current environment
- `uv pip show <package_name>`: Show details about a specific package
- `uv pip freeze > requirements.txt`: Generate a `requirements.txt` file with
  all installed packages
- `uv cache clean`, clear uv's global cache
- `uv cache dir`, show the cache directory
