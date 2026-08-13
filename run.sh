#!/usr/bin/env bash
set -euo pipefail

# Run from the repo root regardless of where this script is invoked from,
# so none of the relative paths used internally (DB path, etc.) break.
cd "$(dirname "${BASH_SOURCE[0]}")"

python3 run_submission.py "$@"
