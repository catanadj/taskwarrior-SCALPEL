#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q scalpel
python -m scalpel.tools.smoke_build --out build/scalpel_smoke.html

echo "OK: compileall + smoke_bu
