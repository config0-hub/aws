#!/bin/bash
# ---------------------------------------------------------------------------
# Build the Lambda deployment zips with Docker, one per handler. Mirrors the
# config0 authoring py_to_lambda-codebuild/docker-to-lambda.sh:
#
#   - STANDALONE (default): docker build each image, then docker create +
#     docker cp the zip out to build/<name>.zip. No live AWS.
#   - UPLOAD_TO_S3=true: additionally upload each zip to S3, so the
#     authoring install stack can run this SAME script under CodeBuild.
#     Uses the presigned PUT URL in PRESIGNED_PUT_<NAME> when presigned_puts.env
#     is present next to this script, else `aws s3 cp` with local creds.
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

LAMBDAS=("$@")
if [ ${#LAMBDAS[@]} -eq 0 ]; then
    LAMBDAS=(starter callback fallback)
fi

# The presigned artifact-upload URLs, when the config0 publisher staged them
# into the source tree. Absent in the standalone workflow.
PRESIGNED_PUTS_FILE="$SCRIPT_DIR/presigned_puts.env"
if [ -f "$PRESIGNED_PUTS_FILE" ]; then
    # shellcheck disable=SC1090
    . "$PRESIGNED_PUTS_FILE"
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
        # A presigned PUT URL authorizes as its signer, so the build needs no
        # IAM grant on the bucket. The URLs arrive in presigned_puts.env inside
        # the source zip rather than as CodeBuild env overrides, which are
        # plaintext and readable by anyone who can describe the build.
        # curl -f + `set -e` fail the build on any non-2xx.
        # Never echo the URL: it is a bearer credential.
        url_var="PRESIGNED_PUT_${name^^}"
        url="${!url_var:-}"
        if [ -n "$url" ]; then
            echo "Uploading ${name}.zip via presigned PUT"
            # --retry-all-errors covers connection resets as well as 429/5xx;
            # --retry gives exponential backoff. -f still fails the build on a
            # 4xx that will never succeed (an expired URL), and `set -e` fails
            # it after the retries are exhausted. The URL is never echoed - it
            # is a bearer credential - so -S's message is the only output, and
            # curl does not print the URL on failure.
            curl -fsS --retry 5 --retry-all-errors \
                 -X PUT -T "${OUT_DIR}/${name}.zip" "$url" \
              || { echo "presigned PUT failed for ${name}.zip after retries" >&2; exit 1; }
        else
            aws s3 cp "${OUT_DIR}/${name}.zip" "s3://${S3_BUCKET}/${KEY_PREFIX}${name}.zip"
        fi
    fi
done

echo "Done. Zips in ${OUT_DIR}:"
ls -l "$OUT_DIR"
