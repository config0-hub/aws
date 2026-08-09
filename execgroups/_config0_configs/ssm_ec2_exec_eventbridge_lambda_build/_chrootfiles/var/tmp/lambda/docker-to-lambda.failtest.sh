#!/bin/bash
# ---------------------------------------------------------------------------
# FAILTEST FIXTURE — deliberately upload CORRUPT lambda zips.
#
# Purpose: reproduce the failed-install orphan case (live run williaumwu_yk9kpb)
# deterministically: the build "succeeds" and uploads all three artifact keys,
# but the payloads are not valid zip archives — so the terraform order creates
# everything declared before the aws_lambda_function resources (DynamoDB,
# EventBridge rules, IAM roles, instance profile, log groups) and then fails on
# Lambda's zip validation. Used ONLY by the ssm-ec2-exec-eventbridge-failtest
# scenario to prove the platform destroy reaches a failed install's partial
# creates. Never referenced by the real install (script_name default is
# docker-to-lambda.sh).
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PRESIGNED_PUTS_FILE="$SCRIPT_DIR/presigned_puts.env"
if [ -f "$PRESIGNED_PUTS_FILE" ]; then
    # shellcheck disable=SC1090
    . "$PRESIGNED_PUTS_FILE"
fi

export S3_BUCKET=${S3_BUCKET:=}
export KEY_PREFIX=${KEY_PREFIX:=}

for name in starter callback fallback; do
    payload="/tmp/${name}.zip"
    echo "FAILTEST: writing corrupt payload for ${name}" > "$payload"

    url_var="PRESIGNED_PUT_$(echo "$name" | tr '[:lower:]' '[:upper:]')"
    url="${!url_var:-}"
    if [ -n "$url" ]; then
        body="/tmp/failtest-put-body-${name}"
        code=$(curl -sS --retry 5 --retry-all-errors -o "$body" -w '%{http_code}' -X PUT -T "$payload" "$url")
        case "$code" in
            2*) echo "FAILTEST: corrupt ${name}.zip uploaded (HTTP ${code})";;
            *)  echo "FAILTEST: upload of ${name}.zip failed with HTTP ${code}" >&2
                cat "$body" >&2
                exit 1;;
        esac
    else
        if [ -z "$S3_BUCKET" ]; then
            echo "FAILTEST: no presigned URL and no S3_BUCKET" >&2
            exit 2
        fi
        aws s3 cp "$payload" "s3://${S3_BUCKET}/${KEY_PREFIX}${name}.zip"
        echo "FAILTEST: corrupt ${name}.zip uploaded via aws s3 cp"
    fi
done

echo "FAILTEST: all three corrupt zips uploaded — terraform will partially create, then fail on Lambda zip validation."
