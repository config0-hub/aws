#!/bin/bash
# ---------------------------------------------------------------------------
# Build the Lambda deployment zips with Docker, one per handler. Mirrors the
# config0 authoring py_to_lambda-codebuild/docker-to-lambda.sh:
#
#   - STANDALONE (default): docker build each image, then docker create +
#     docker cp the zip out to build/<name>.zip. No live AWS.
#   - UPLOAD_TO_S3=true: additionally upload each zip to S3 with `aws s3 cp`,
#     so the authoring install stack can run this SAME script under CodeBuild
#     (the build's own credentials, exactly like the original
#     py_to_lambda-codebuild/docker-to-lambda.sh).
#
# Usage:
#   docker-to-lambda.sh                 # build all three lambdas
#   docker-to-lambda.sh starter         # build one
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHON_VERSION=${PYTHON_VERSION:=3.12}
export OUT_DIR=${OUT_DIR:=$TOOL_DIR/build}
export DOCKERFILE_LAMBDA=${DOCKERFILE_LAMBDA:=$SCRIPT_DIR/Dockerfile}
# UPLOAD_TO_S3 (renamed from CODEBUILD_ENV): the config0 CodeBuild submitter
# strips every env var matching ^CODEBUILD (reserved prefix), so the old guard
# name silently never arrived in the build. Same semantics.
export UPLOAD_TO_S3=${UPLOAD_TO_S3:=false}
export S3_BUCKET=${S3_BUCKET:=}
# KEY_PREFIX lets the config0 install stack scope the uploaded zips under a
# per-execution prefix (e.g. "<execution_id>/"), so a fresh build -> fresh key
# -> terraform sees a changed s3_key and rolls the code out. Default empty
# keeps the standalone behavior (upload to the bucket root).
export KEY_PREFIX=${KEY_PREFIX:=}
# METHOD rides the SOPS-sealed build env (the install stack's build_envs), not
# the parent process: CodeBuild never sees the CLI's METHOD. On a destroy run
# the install job re-emits this order; there is nothing here to tear down (the
# zips live in the artifact bucket the stack's bucket job deletes), so print
# the markers the CLI's execgroup destroy finalizer reads from the engine
# ExecutionResult and stop - no docker build, no upload.
METHOD="${METHOD:-create}"
if [ "$METHOD" = "destroy" ]; then
    echo "CONFIG0_DESTROY_PRE_STATE_COUNT=0"
    echo "CONFIG0_DESTROY_POST_STATE_COUNT=0"
    exit 0
fi

LAMBDAS=("$@")
if [ ${#LAMBDAS[@]} -eq 0 ]; then
    LAMBDAS=(starter callback fallback)
fi

mkdir -p "$OUT_DIR"

for name in "${LAMBDAS[@]}"; do
    image="ssm-ec2-exec-eventbridge-lambda-${name}"
    container="${image}-run"

    echo "######################################################"
    echo "# Building lambda zip: ${name}"
    echo "# python_version => ${PYTHON_VERSION}"
    echo "# out            => ${OUT_DIR}/${name}.zip"
    echo "######################################################"

    docker build -f "$DOCKERFILE_LAMBDA" \
                 --target export \
                 --build-arg pkg_name="$name" \
                 --build-arg src_dir="$name" \
                 --build-arg python_version="$PYTHON_VERSION" \
                 -t "$image" \
                 "$SCRIPT_DIR"

    docker rm -f "$container" >/dev/null 2>&1 || true
    docker create --name "$container" "$image" >/dev/null
    docker cp "${container}:/lambda.zip" "${OUT_DIR}/${name}.zip"
    docker rm "$container" >/dev/null

    if [ "$UPLOAD_TO_S3" = "true" ]; then
        if [ -z "$S3_BUCKET" ]; then
            echo "UPLOAD_TO_S3=true but S3_BUCKET is unset" >&2
            exit 2
        fi
        aws s3 cp "${OUT_DIR}/${name}.zip" "s3://${S3_BUCKET}/${KEY_PREFIX}${name}.zip"
    fi
done

echo "Done. Zips in ${OUT_DIR}:"
ls -l "$OUT_DIR"
