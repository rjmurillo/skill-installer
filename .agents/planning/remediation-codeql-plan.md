# Plan: Clear CodeQL cyclic import findings

## Scope
- Resolve py/unsafe-cyclic-import between install.py and protocols.py by relocating shared types.
- Preserve behavior and existing tests.

## Steps
1) Extract InstallResult dataclass to a new neutral module (src/skill_installer/types.py).
2) Update install.py to import InstallResult from types and keep FileSystem import safe.
3) Update protocols.py to import InstallResult from types without cycles.
4) Update tests and other imports to use skill_installer.types.InstallResult.
5) Run pytest (quick) and rerun `.codeql/scripts/run-codeql.sh`; report findings.

## Acceptance Criteria
- CodeQL scan reports zero py/unsafe-cyclic-import findings.
- Unit tests pass.
