#!/usr/bin/env bash
# Everything deterministic in this repo, in one command.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 tests/test_validate_record.py "$@"
python3 tests/test_hook.py "$@"
python3 tests/test_hunt_lock.py "$@"

# The clean fixture is validated in a clean throwaway repository because Tree:
# deliberately binds a record to the repository state it describes.
FIXTURE_REPO=$(mktemp -d "${TMPDIR:-/tmp}/groundwork-fixture.XXXXXX")
trap 'rm -rf "$FIXTURE_REPO"' EXIT
git -C "$FIXTURE_REPO" init -q
printf '.groundwork/\n' > "$FIXTURE_REPO/.gitignore"
git -C "$FIXTURE_REPO" -c user.name=Test -c user.email=test@example.com \
  add .gitignore
git -C "$FIXTURE_REPO" -c user.name=Test -c user.email=test@example.com \
  commit -qm base
mkdir -p "$FIXTURE_REPO/.groundwork"
cp tests/fixtures/clean.md "$FIXTURE_REPO/.groundwork/record.md"
python3 skills/groundwork/scripts/validate_record.py \
  "$FIXTURE_REPO/.groundwork/record.md"

# The template has to stay invalid: a half-filled record must not pass.
if python3 skills/groundwork/scripts/validate_record.py templates/RECORD.template.md --quiet; then
  echo "test.sh: the template validated — placeholders are no longer caught" >&2
  exit 1
fi
echo "template correctly rejected while placeholders remain"
