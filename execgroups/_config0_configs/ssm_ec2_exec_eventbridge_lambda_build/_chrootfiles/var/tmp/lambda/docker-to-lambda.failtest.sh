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

export S3_BUCKET=${S3_BUCKET:=}
export KEY_PREFIX=${KEY_PREFIX:=}

if [ -z "$S3_BUCKET" ]; then
    echo "FAILTEST: S3_BUCKET is unset" >&2
    exit 2
fi

for name in starter callback fallback; do
    payload="/tmp/${name}.zip"
    echo "FAILTEST: writing corrupt payload for ${name}" > "$payload"

    aws s3 cp "$payload" "s3://${S3_BUCKET}/${KEY_PREFIX}${name}.zip"
    echo "FAILTEST: corrupt ${name}.zip uploaded via aws s3 cp"
done

echo "FAILTEST: all three corrupt zips uploaded — terraform will partially create, then fail on Lambda zip validation."
