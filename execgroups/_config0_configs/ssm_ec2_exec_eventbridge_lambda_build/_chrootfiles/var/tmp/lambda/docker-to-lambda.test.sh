#!/bin/bash
# ---------------------------------------------------------------------------
# Self-contained check for docker-to-lambda.sh's UPLOAD_TO_S3 branch: does it
# take the presigned PUT when presigned_puts.env is staged, and fall back to
# `aws s3 cp` when it is not?
#
# This repo has no bats or shell-test runner, so this runs itself:
#     bash docker-to-lambda.test.sh
# It stubs docker/curl/aws on PATH — nothing is built, nothing is uploaded.
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

# curl / aws just record how they were called.
# curl stub: records the call and emits the HTTP code the test asked for via
# CURL_FAKE_CODE, writing a body to the -o path like the real thing.
cat > "$STUB_DIR/curl" <<STUB
#!/bin/bash
echo "curl \$*" >> "$WORK/calls"
out=""
prev=""
for a in "\$@"; do
    [ "\$prev" = "-o" ] && out="\$a"
    prev="\$a"
done
[ -n "\$out" ] && echo "<Error><Code>TemporaryRedirect</Code></Error>" > "\$out"
printf '%s' "\${CURL_FAKE_CODE:-200}"
STUB
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
      && PATH="$STUB_DIR:$PATH" UPLOAD_TO_S3=true S3_BUCKET=a-bucket \
         KEY_PREFIX="exec-1/" OUT_DIR="$WORK/out" \
         CURL_FAKE_CODE="${CURL_FAKE_CODE:-200}" \
         ./docker-to-lambda.sh starter >/dev/null 2>"$WORK/stderr" )
    rc=$?
    cat "$WORK/calls"
    return $rc
}

fail() { echo "FAIL: $1" >&2; exit 1; }

# 1. No presigned_puts.env -> `aws s3 cp` fallback (the standalone workflow).
rm -f "$RUN_DIR/presigned_puts.env"
calls="$(run_script || true)"
[[ "$calls" == *"aws s3 cp"* ]] || fail "no presigned file: expected the aws s3 cp fallback, got: $calls"
[[ "$calls" != *"curl"* ]] || fail "no presigned file: curl was used anyway"

# 2. presigned_puts.env staged -> curl PUT to the signed URL, no aws s3 cp.
printf "export PRESIGNED_PUT_STARTER='https://example/starter.zip?sig=abc'\n" \
    > "$RUN_DIR/presigned_puts.env"
calls="$(run_script || true)"
[[ "$calls" == *"curl"*"https://example/starter.zip?sig=abc"* ]] || fail "presigned file staged: expected a curl PUT, got: $calls"
[[ "$calls" != *"aws s3 cp"* ]] || fail "presigned file staged: fell back to aws s3 cp anyway"

# 3. A file naming OTHER lambdas must not make this one use a stale URL.
printf "export PRESIGNED_PUT_CALLBACK='https://example/callback.zip'\n" \
    > "$RUN_DIR/presigned_puts.env"
calls="$(run_script || true)"
[[ "$calls" == *"aws s3 cp"* ]] || fail "unrelated presigned entry: expected the fallback, got: $calls"

# 4. A non-2xx response must FAIL the build. The 307 that started this: curl -f
#    does not fail on a 3xx, so only the response-code check catches it.
printf "export PRESIGNED_PUT_STARTER='https://example/starter.zip?sig=abc'\n" \
    > "$RUN_DIR/presigned_puts.env"
for code in 307 403 500; do
    if CURL_FAKE_CODE="$code" run_script >/dev/null 2>&1; then
        fail "HTTP $code was treated as a successful upload"
    fi
    grep -q "failed with HTTP $code" "$WORK/stderr" || fail "HTTP $code: error did not name the code"
    grep -q "sig=abc" "$WORK/stderr" && fail "HTTP $code: the presigned URL was printed"
done

echo "OK: both upload branches behave, non-2xx fails loud"
