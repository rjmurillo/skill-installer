#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CODEQL_DIR="$ROOT_DIR/.codeql"
DB="$CODEQL_DIR/skill-installer-codeql-db"
SARIF=$CODEQL_DIR/skill-installer-codeql.sarif
export SARIF

mkdir -p "$CODEQL_DIR"
rm -rf "$DB" "$SARIF"

echo "[codeql] Downloading packs..." >&2
gh codeql pack download codeql/python-queries@latest codeql/python-all@latest

echo "[codeql] Creating database at $DB..." >&2
gh codeql database create "$DB" --language=python --source-root "$ROOT_DIR" --overwrite

echo "[codeql] Analyzing to $SARIF..." >&2
gh codeql database analyze "$DB" \
  codeql/python-queries:codeql-suites/python-security-extended.qls \
  codeql/python-queries:codeql-suites/python-security-and-quality.qls \
  --format=sarifv2.1.0 --output "$SARIF" --sarif-category=python --threads=0 --ram=6000

echo "[codeql] Summary of findings:" >&2
python3 - <<'PY'
import json, collections, pathlib, os
sarif = pathlib.Path(os.environ['SARIF'])
if not sarif.exists():
    raise SystemExit('SARIF missing at ' + str(sarif))
data = json.loads(sarif.read_text())
counts = collections.Counter()
sev = {}
for run in data.get('runs', []):
    rules = {r.get('id'): r for r in run.get('tool', {}).get('driver', {}).get('rules', [])}
    for rid, rule in rules.items():
        sev[rid] = rule.get('properties', {}).get('problem.severity') or rule.get('defaultConfiguration', {}).get('severity')
    for res in run.get('results', []):
        counts[res.get('ruleId')] += 1
for rid, cnt in counts.most_common():
    print(f"{rid}: {cnt} (severity {sev.get(rid)})")
print('\nSample locations:')
for run in data.get('runs', []):
    for res in run.get('results', [])[:5]:
        loc = res.get('locations', [{}])[0].get('physicalLocation', {}).get('artifactLocation', {}).get('uri')
        start = res.get('locations', [{}])[0].get('physicalLocation', {}).get('region', {}).get('startLine')
        print(f"{res.get('ruleId')}: {loc}:{start}")

# Exit non-zero if error or warning severity findings exist
blocking_severities = {'error', 'critical', 'high', 'warning'}
blocking_count = sum(cnt for rid, cnt in counts.items() if sev.get(rid) in blocking_severities)
if blocking_count > 0:
    print(f"\n{blocking_count} blocking issue(s) found. Push blocked.", file=__import__('sys').stderr)
    raise SystemExit(1)
print("\nNo blocking issues found.")
PY
