# CodeQL setup and usage

This project mirrors GitHub's Code Scanning configuration. Use the helper script for local parity with the GitHub workflow.

## Prerequisites
- `gh` CLI with the `github/gh-codeql` extension (CodeQL CLI >= 2.23.9).
- Authenticated `gh` so pack downloads work (`GH_TOKEN`/`GITHUB_TOKEN`).

## Configuration reference
- Workflow: `.github/workflows/codeql.yml` uses `config-file: .github/codeql/codeql-config.yml`.
- Config: `.github/codeql/codeql-config.yml` selects `security-extended` and `security-and-quality` queries and includes pack `codeql/python-all`.
- Suites for parity: `codeql/python-queries:codeql-suites/python-security-extended.qls` and `codeql/python-queries:codeql-suites/python-security-and-quality.qls`.

## One-shot local run
Artifacts are stored under `.codeql/` for easy discovery.
```bash
.codeql/scripts/run-codeql.sh
```
- Database: `.codeql/skill-installer-codeql-db`
- SARIF: `.codeql/skill-installer-codeql.sarif`

## Notes
- The CLI expects explicit suites; the config file is used by GitHub Actions.
- Recent local run examples (Jan 17, 2026): `py/unsafe-cyclic-import`, `py/ineffectual-statement`, `py/unused-import`.
- Remove existing DB (`rm -rf .codeql/skill-installer-codeql-db`) before recreating to avoid "not a recognized CodeQL database" errors.
