#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/lint_skills.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
