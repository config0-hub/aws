#!/bin/bash
# ssm_ec2_exec remote wrapper — fixed bootstrap embedded verbatim as the
# SendCommand "script" line (self-contained: no sibling files exist on the
# target, everything below travels in this one string). Never traces (no
# set -x), never echoes $TASK_TOKEN. The payload is always S3-staged;
# nothing user-supplied is interpolated into a shell string here.
#
# Expects these already exported ahead of this script: TASK_TOKEN (by the
# ASL), S3_BUCKET / S3_KEY_PREFIX / AWS_REGION / EXECUTION_ID (by the CLI).
set -uo pipefail

WORKDIR=$(mktemp -d)
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

fail_infra() {
    # Wrapper-infrastructure failure (download/parse never got as far as
    # running the payload) — the ONLY case that calls send-task-failure.
    local reason="$1"
    aws stepfunctions send-task-failure \
        --task-token "$TASK_TOKEN" \
        --error "WrapperInfraFailure" \
        --cause "$reason" \
        --region "$AWS_REGION" >/dev/null 2>&1 || true
    exit 1
}

aws s3 cp "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/payload" "$WORKDIR/payload.json" \
    --region "$AWS_REGION" --only-show-errors || fail_infra "payload download failed"

# Decode the payload into $WORKDIR: commands/script -> run.sh, ansible ->
# ansible/ (safe-extracted) + playbook_name.txt. Writes payload_type.txt
# last so a partial decode never looks complete.
# F6 remediation: the remote side re-enforces the exact same wire contract
# the CLI's pydantic model does — schema_version must be exactly 1, exactly
# one payload variant may be present, base64 is decoded strictly (rejects
# padding/alphabet errors instead of silently truncating), the ansible
# variant requires its sha256 and the 64MiB decoded-zip cap is re-checked
# here (the CLI's own cap is not a substitute — nothing trusts the sender).
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

# F3 remediation: TASK_TOKEN is a bearer credential — it must never reach
# payload code (an `env`/`echo $TASK_TOKEN` command could exfiltrate it via
# stdout.log or call the callback itself). `env -u` strips it from the
# child's environment only; the wrapper's own shell keeps it for the
# callback below.
set +e
if [ "$PAYLOAD_TYPE" = "ansible" ]; then
    PLAYBOOK=$(cat "$WORKDIR/playbook_name.txt")
    ( cd "$WORKDIR/ansible" && env -u TASK_TOKEN ansible-playbook "$PLAYBOOK" ) \
        >"$WORKDIR/stdout.log" 2>"$WORKDIR/stderr.log"
    EXIT_CODE=$?
else
    chmod +x "$WORKDIR/run.sh"
    env -u TASK_TOKEN "$WORKDIR/run.sh" >"$WORKDIR/stdout.log" 2>"$WORKDIR/stderr.log"
    EXIT_CODE=$?
fi
set -e

FINISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Derive our own SSM CommandId from the orchestration working-directory path
# (.../document/orchestration/<command-id>/...) — no ssm:List*/Get* IAM grant
# is needed for this. Falls back to "unknown" if the pattern doesn't match;
# a manifest without it is still trustworthy.
COMMAND_ID=$(pwd | grep -oE '/orchestration/[0-9a-f-]+/' | head -1 | tr -d '/' | sed 's/^orchestration//' || true)
COMMAND_ID=${COMMAND_ID:-unknown}

STATUS="failed"
if [ "$EXIT_CODE" -eq 0 ]; then
    STATUS="succeeded"
fi

# Manifest written BEFORE the callback: a lost/denied/late callback still
# leaves a trustworthy result in S3.
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

# F2 remediation: upload the actual captured streams (manifest.log_keys
# only ever advertised these two keys — now they really exist in S3).
aws s3 cp "$WORKDIR/stdout.log" "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/stdout.log" \
    --region "$AWS_REGION" --only-show-errors || fail_infra "stdout upload failed"
aws s3 cp "$WORKDIR/stderr.log" "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/stderr.log" \
    --region "$AWS_REGION" --only-show-errors || fail_infra "stderr upload failed"

aws s3 cp "$WORKDIR/manifest.json" "s3://${S3_BUCKET}/${S3_KEY_PREFIX}/manifest.json" \
    --region "$AWS_REGION" --only-show-errors || fail_infra "manifest upload failed"

TASK_OUTPUT=$(python3 -c 'import json,sys; print(json.dumps({"exit_code": int(sys.argv[1]), "command_id": sys.argv[2]}))' "$EXIT_CODE" "$COMMAND_ID")

CALLBACK_OK=0
for attempt in 1 2 3; do
    if aws stepfunctions send-task-success \
        --task-token "$TASK_TOKEN" \
        --task-output "$TASK_OUTPUT" \
        --region "$AWS_REGION" >/dev/null 2>&1; then
        CALLBACK_OK=1
        break
    fi
    sleep 2
done

if [ "$CALLBACK_OK" -eq 0 ]; then
    # The payload itself ran and the manifest is already durable in S3; this
    # is the callback-transport failing, which IS wrapper-infrastructure —
    # best-effort send-task-failure so the state machine doesn't hang until
    # its own timeout. The wrapper's own exit code still reflects the
    # payload's real result (preserved from the manifest), since that is
    # what actually happened on the box, independent of whether the
    # callback made it back.
    aws stepfunctions send-task-failure \
        --task-token "$TASK_TOKEN" \
        --error "WrapperInfraFailure" \
        --cause "send-task-success failed after retries" \
        --region "$AWS_REGION" >/dev/null 2>&1 || true
fi

exit "$EXIT_CODE"
