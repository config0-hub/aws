#!/bin/bash
# ssm_ec2_exec_eventbridge remote wrapper — fixed bootstrap embedded verbatim
# as the SendCommand "script" line (self-contained: no sibling files exist on
# the target, everything below travels in this one string). Never traces (no
# set -x).
#
# v2 delta from v1: NO task token reaches the box, and the wrapper never calls
# Step Functions. It downloads the payload, runs it, writes stdout/stderr and a
# result manifest to S3, and exits with the payload's exit code. That exit code
# becomes the SSM command's ResponseCode, which the server-side callback/
# fallback Lambdas read to release the Step Functions task. An infra failure
# (download/prepare/upload) records status:"infra_failure" in the manifest,
# echoes the reason to stderr (SSM captures it), and exits 1.
#
# Expects these already exported ahead of this script (by the CLI-built
# `script` field): S3_BUCKET / S3_KEY_PREFIX / AWS_REGION / EXECUTION_ID.
set -uo pipefail

WORKDIR=$(mktemp -d)
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

fail_infra() {
    # Wrapper-infrastructure failure (download/prepare/upload never got as far
    # as a real payload result). Records an infra_failure manifest so the CLI
    # can attribute it, echoes the reason to stderr, and exits 1 — no Step
    # Functions API is ever called (v2 keeps the token server-side).
    local reason="$1"
    echo "infra_failure: $reason" 1>&2
    local sha=""
    if [ -f "$WORKDIR/payload_sha256.txt" ]; then
        sha=$(cat "$WORKDIR/payload_sha256.txt")
    fi
    local finished
    finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    python3 - "$WORKDIR" "$EXECUTION_ID" "$sha" "$STARTED_AT" "$finished" "$reason" <<'INFRA_PY' || true
import json, sys
from pathlib import Path

workdir, execution_id, sha, started_at, finished_at, reason = sys.argv[1:7]
manifest = {
    "schema_version": 1,
    "execution_id": execution_id,
    "payload_sha256": sha,
    "exit_code": 1,
    "status": "infra_failure",
    "started_at": started_at,
    "finished_at": finished_at,
    "reason": reason,
    "log_keys": [],
}
(Path(workdir) / "manifest.json").write_text(json.dumps(manifest))
INFRA_PY
    aws s3 cp "$WORKDIR/manifest.json" "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/manifest.json" \
        --region "$AWS_REGION" --only-show-errors >/dev/null 2>&1 || true
    exit 1
}

aws s3 cp "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/payload" "$WORKDIR/payload.json" \
    --region "$AWS_REGION" --only-show-errors || fail_infra "payload download failed"

# Decode the payload into $WORKDIR: commands/script -> run.sh, ansible ->
# ansible/ (safe-extracted) + playbook_name.txt. Writes payload_type.txt
# last so a partial decode never looks complete.
# The remote side re-enforces the exact same wire contract the CLI's pydantic
# model does — schema_version must be exactly 1, exactly one payload variant
# may be present, base64 is decoded strictly (rejects padding/alphabet errors
# instead of silently truncating), the ansible variant requires its sha256 and
# the 64MiB decoded-zip cap is re-checked here (nothing trusts the sender).
ANSIBLE_ZIP_MAX_BYTES=$((64 * 1024 * 1024))
python3 - "$WORKDIR" "$ANSIBLE_ZIP_MAX_BYTES" <<'PREPARE_PY' || fail_infra "payload prepare failed"
import base64, binascii, hashlib, json, os, sys, zipfile
from pathlib import Path

workdir = Path(sys.argv[1])
ansible_zip_max_bytes = int(sys.argv[2])
raw_payload = (workdir / "payload.json").read_bytes()
(workdir / "payload_sha256.txt").write_text(hashlib.sha256(raw_payload).hexdigest())
payload = json.loads(raw_payload)

if payload.get("schema_version") != 1:
    raise SystemExit(f"unsupported schema_version: {payload.get('schema_version')!r}")

ptype = payload.get("payload_type")
variants = {
    "commands": payload.get("commands_b64") is not None,
    "script": payload.get("script_b64") is not None,
    "ansible": payload.get("ansible_zip_b64") is not None,
}
if ptype not in variants:
    raise SystemExit(f"unknown payload_type: {ptype!r}")
if not variants[ptype]:
    raise SystemExit(f"payload_type={ptype!r} but its field is empty")
if sum(variants.values()) != 1:
    raise SystemExit(f"exactly one payload variant required, got {variants}")


def strict_b64decode(value: str, what: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SystemExit(f"invalid base64 in {what}: {exc}")


if ptype == "commands":
    lines = [strict_b64decode(x, "commands_b64").decode() for x in payload["commands_b64"]]
    script = "#!/bin/bash\nset -euo pipefail\n" + "\n".join(lines) + "\n"
    (workdir / "run.sh").write_text(script)
elif ptype == "script":
    (workdir / "run.sh").write_bytes(strict_b64decode(payload["script_b64"], "script_b64"))
elif ptype == "ansible":
    expected = payload.get("ansible_zip_sha256")
    if not expected:
        raise SystemExit("ansible payload requires ansible_zip_sha256")
    raw = strict_b64decode(payload["ansible_zip_b64"], "ansible_zip_b64")
    if len(raw) > ansible_zip_max_bytes:
        raise SystemExit(f"ansible zip is {len(raw)} bytes, exceeds cap of {ansible_zip_max_bytes}")
    if hashlib.sha256(raw).hexdigest() != expected:
        raise SystemExit("ansible zip sha256 mismatch")
    zip_path = workdir / "playbook.zip"
    zip_path.write_bytes(raw)
    extract_dir = workdir / "ansible"
    extract_dir.mkdir()
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            p = Path(name)
            if p.is_absolute() or p.drive or ".." in p.parts:
                raise SystemExit(f"unsafe zip entry: {name}")
        zf.extractall(extract_dir)
    playbook = payload.get("playbook") or "site.yml"
    # Constrain the playbook argument to a safe relative member of the
    # extracted tree — no leading "-" (argument-option injection into
    # ansible-playbook) and no path escape.
    pb_path = Path(playbook)
    if playbook.startswith("-") or pb_path.is_absolute() or pb_path.drive or ".." in pb_path.parts:
        raise SystemExit(f"unsafe playbook member: {playbook!r}")
    if not (extract_dir / pb_path).is_file():
        raise SystemExit(f"playbook not found in extracted zip: {playbook!r}")
    (workdir / "playbook_name.txt").write_text(playbook)
else:
    raise SystemExit(f"unknown payload_type: {ptype}")

(workdir / "payload_type.txt").write_text(ptype)
PREPARE_PY

PAYLOAD_TYPE=$(cat "$WORKDIR/payload_type.txt")

# Run the payload with a clean env: the wrapper's own staging variables are
# stripped from the child so payload code never inherits them. (v2 has no
# server-side callback credential on the box, but keeping the payload's env
# clean of the wrapper's internals is still the right default.)
set +e
if [ "$PAYLOAD_TYPE" = "ansible" ]; then
    PLAYBOOK=$(cat "$WORKDIR/playbook_name.txt")
    ( cd "$WORKDIR/ansible" && env -u S3_BUCKET -u S3_KEY_PREFIX -u EXECUTION_ID ansible-playbook "$PLAYBOOK" ) \
        >"$WORKDIR/stdout.log" 2>"$WORKDIR/stderr.log"
    EXIT_CODE=$?
else
    chmod +x "$WORKDIR/run.sh"
    env -u S3_BUCKET -u S3_KEY_PREFIX -u EXECUTION_ID "$WORKDIR/run.sh" \
        >"$WORKDIR/stdout.log" 2>"$WORKDIR/stderr.log"
    EXIT_CODE=$?
fi
set -e

FINISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Derive our own SSM CommandId from the orchestration working-directory path
# (.../document/orchestration/<command-id>/...) — no ssm:List*/Get* IAM grant
# is needed for this. Falls back to "unknown" if the pattern doesn't match.
COMMAND_ID=$(pwd | grep -oE '/orchestration/[0-9a-f-]+/' | head -1 | tr -d '/' | sed 's/^orchestration//' || true)
COMMAND_ID=${COMMAND_ID:-unknown}

STATUS="failed"
if [ "$EXIT_CODE" -eq 0 ]; then
    STATUS="succeeded"
fi

python3 - "$WORKDIR" "$EXECUTION_ID" "$EXIT_CODE" "$STATUS" "$STARTED_AT" "$FINISHED_AT" "$COMMAND_ID" <<'MANIFEST_PY' || fail_infra "manifest build failed"
import json, sys
from pathlib import Path

workdir, execution_id, exit_code, status, started_at, finished_at, command_id = sys.argv[1:8]
payload_sha256 = (Path(workdir) / "payload_sha256.txt").read_text().strip()
manifest = {
    "schema_version": 1,
    "execution_id": execution_id,
    "payload_sha256": payload_sha256,
    "exit_code": int(exit_code),
    "status": status,
    "started_at": started_at,
    "finished_at": finished_at,
    "command_id": command_id,
    "log_keys": ["stdout.log", "stderr.log"],
}
(Path(workdir) / "manifest.json").write_text(json.dumps(manifest))
MANIFEST_PY

aws s3 cp "$WORKDIR/stdout.log" "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/stdout.log" \
    --region "$AWS_REGION" --only-show-errors || fail_infra "stdout upload failed"
aws s3 cp "$WORKDIR/stderr.log" "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/stderr.log" \
    --region "$AWS_REGION" --only-show-errors || fail_infra "stderr upload failed"

aws s3 cp "$WORKDIR/manifest.json" "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/manifest.json" \
    --region "$AWS_REGION" --only-show-errors || fail_infra "manifest upload failed"

exit "$EXIT_CODE"
