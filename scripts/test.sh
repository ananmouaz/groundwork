#!/usr/bin/env bash
# Everything deterministic in this repo, in one command.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 tests/test_validate_record.py "$@"
python3 tests/test_hook.py "$@"

# The example in the README has to stay valid, or the README teaches a record
# the validator rejects.
python3 skills/groundwork/scripts/validate_record.py tests/fixtures/clean.md

# The template has to stay invalid: a half-filled record must not pass.
if python3 skills/groundwork/scripts/validate_record.py templates/RECORD.template.md --quiet; then
  echo "test.sh: the template validated — placeholders are no longer caught" >&2
  exit 1
fi
echo "template correctly rejected while placeholders remain"
