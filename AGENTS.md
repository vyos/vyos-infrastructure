# AGENTS.md

## Project purpose
Public scripts and automations for VyOS project infrastructure tasks — primarily Phorge (Phabricator fork) housekeeping and license-report generation. Not part of the VyOS image build; runs as scheduled GitHub Actions against external services.

## Tech stack
- Python 3 with stdlib + minimal third-party deps. `phabricator_tasks/requirements.txt` declares the runtime libraries.
- No `pyproject.toml`, no Debian packaging, no `setup.py` — scripts are run directly.
- GitHub Actions: `phabricator_tasks.yml` (scheduled), `cla-check.yml`.

## Build / test / run
```
pip install -r phabricator_tasks/requirements.txt
python phabricator_tasks/tasks.py
python phabricator_tasks/get_task_data.py
python license-report.py
```
No test suite.

## Repository layout
- `phabricator_tasks/`
  - `tasks.py` — chores: marks tasks resolved when present in "Finished" columns on all boards; unassigns long-stale assigned tasks.
  - `get_task_data.py` — read-only Phorge data fetcher.
  - `requirements.txt` — Python deps.
- `license-report.py` — license-report generator.
- `LICENSE`, `README.md`.
- `.github/workflows/phabricator_tasks.yml` — schedule + workflow.

## Cross-repo context
- Talks to the Phorge instance at https://vyos.dev (Conduit API). Phorge is the canonical task tracker referenced by the `component: T12345: description` commit convention enforced across every other VyOS repo via `vyos/.github`.
- Adjacent in role to `VyOS-Networks/big-beautiful-order` (Phorge task version-tag auditor) and `VyOS-Networks/cve-checker`. None of these are part of the build pipeline; they are governance tooling.
- `cla-check.yml` delegates to `vyos/vyos-cla-signatures/.github/workflows/cla-reusable.yml@current`.

## Conventions
- Commit/PR title: `component: T12345: description` (Phorge task ID at https://vyos.dev) where applicable.
- Default branch: confirm via `git ls-remote --symref`. Treat as a single-track repo (no LTS branches).
- Public repo: never commit Phorge API tokens, Conduit certificates, or service-account credentials. Inject via GitHub Actions secrets only.

## Mirror relationship
Mirror twin: `VyOS-Networks/vyos-infrastructure`. The mirror is largely independent (hosts HCL/Ansible IaC for internal infra); this `vyos/*` side is the public housekeeping scripts only. Do not assume code parity.

## Notes for future contributors
- Phorge API endpoints can change without notice — pin `requirements.txt` and re-test scheduled jobs after any Phorge upgrade.
- Avoid embedding board PHIDs or task IDs as constants — read them from config or workflow inputs.
- Adjacent VyOS-side automation (CVE tracking, release process) lives under `VyOS-Networks/cve-checker` and `VyOS-Networks/vyos-release-process`. Coordinate with their maintainers before duplicating logic.
