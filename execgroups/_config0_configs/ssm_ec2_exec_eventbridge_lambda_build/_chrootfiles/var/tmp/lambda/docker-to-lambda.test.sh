#!/bin/bash
# ---------------------------------------------------------------------------
# Self-contained check for docker-to-lambda.sh's UPLOAD_TO_S3 branch: does it
# upload each zip with `aws s3 cp` to the right bucket/key, and fail loud when
# S3_BUCKET is unset?
#
# This repo has no bats or shell-test runner, so this runs itself:
#     bash docker-to-lambda.test.sh
# It stubs docker/aws on PATH — nothing is built, nothing is uploaded.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

STUB_DIR="$WORK/bin"
mkdir -p "$STUB_DIR" "$WORK/tool/lambdas"

# docker: `build` does nothing; `create` prints a container id; `cp` writes a
# stand-in zip; `rm` does nothing.
cat > "$STUB_DIR/docker" <<'STUB'
#!/bin/bash
case "$1" in
  cp) printf 'zip\n' > "${@: -1}" ;;
  create) echo "container-id" ;;
esac
exit 0
STUB

# aws just records how it was called.
cat > "$STUB_DIR/aws" <<STUB
#!/bin/bash
echo "aws \$*" >> "$WORK/calls"
STUB
chmod 755 "$STUB_DIR"/*

RUN_DIR="$WORK/tool/lambdas"
cp "$SCRIPT_DIR/docker-to-lambda.sh" "$RUN_DIR/"
: > "$RUN_DIR/Dockerfile"

run_script() {
    rm -f "$WORK/calls"
    ( cd "$RUN_DIR" \
      && PATH="$STUB_DIR:$PATH" UPLOAD_TO_S3="${UPLOAD_TO_S3:-true}" \
         S3_BUCKET="${S3_BUCKET-a-bucket}" \
         KEY_PREFIX="exec-1/" OUT_DIR="$WORK/out" \
         ./docker-to-lambda.sh starter >/dev/null 2>"$WORK/stderr" )
    rc=$?
    [ -f "$WORK/calls" ] && cat "$WORK/calls"
    return $rc
}

fail() { echo "FAIL: $1" >&2; exit 1; }

# 1. UPLOAD_TO_S3=true -> `aws s3 cp` to the bucket under KEY_PREFIX.
calls="$(run_script || true)"
[[ "$calls" == *"aws s3 cp"*"s3://a-bucket/exec-1/starter.zip"* ]] \
    || fail "expected an aws s3 cp to s3://a-bucket/exec-1/starter.zip, got: $calls"

# 2. UPLOAD_TO_S3=false (standalone) -> no upload at all.
calls="$(UPLOAD_TO_S3=false run_script || true)"
[[ "$calls" != *"aws s3 cp"* ]] || fail "standalone run uploaded anyway: $calls"

# 3. UPLOAD_TO_S3=true with S3_BUCKET unset -> fail loud.
if S3_BUCKET="" run_script >/dev/null 2>&1; then
    fail "unset S3_BUCKET was not an error"
fi
grep -q "S3_BUCKET is unset" "$WORK/stderr" || fail "unset S3_BUCKET: error did not name the cause"

echo "OK: the upload branch uses aws s3 cp, standalone skips it, unset bucket fails loud"
