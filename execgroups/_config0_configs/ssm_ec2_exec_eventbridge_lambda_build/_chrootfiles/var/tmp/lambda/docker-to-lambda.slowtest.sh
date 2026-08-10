#!/bin/bash
# ---------------------------------------------------------------------------
# SLOWTEST FIXTURE - a real build, deliberately padded past the old 900s cap.
#
# Purpose: prove the deadline-driven done-marker watch. The worker's watch
# deadline used to be a hard 900s, so a CodeBuild-delegated order whose build
# ran longer was requeued mid-flight and fired a second time. The deadline now
# derives from the order's own timeout (run.py: build_timeout + 600), so a long
# build must park once and finalize once.
#
# This runs the REAL docker-to-lambda.sh first, then sleeps. Build-then-sleep
# (not sleep-then-build) so a broken build fails in minutes instead of costing
# the full pad. The done-marker follows the CodeBuild build reaching a terminal
# state, so the sleep extends the parked window exactly as intended.
#
# Selected per-run via the install stack's `script_name` argument. Never
# referenced by the real install (script_name default is docker-to-lambda.sh).
# SLOWTEST_SLEEP overrides the pad; the default alone clears 900s.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The engine only chmods the script named by SCRIPT_NAME, so invoke the real
# builder through bash rather than relying on its exec bit surviving the zip.
bash "$SCRIPT_DIR/docker-to-lambda.sh" "$@"

SLOWTEST_SLEEP=${SLOWTEST_SLEEP:=1200}
echo "SLOWTEST: build done, padding ${SLOWTEST_SLEEP}s to push the parked window past the retired 900s watch cap"
sleep "$SLOWTEST_SLEEP"
echo "SLOWTEST: pad complete"
