#!/bin/bash
# ---------------------------------------------------------------------------
# Copy the released openci-tf Lambda image from GHCR into the tenant ECR
# repository. Mirrors openci-tf's scripts/copy_ghcr_image.sh, but standalone
# for the config0 execgroup: the GHCR reference and the ECR tag arrive as
# environment variables from the openci_tf_install stack (no openci-tf
# checkout inside the CodeBuild container). Runs under CodeBuild through the
# codebuild-srcfile script, privileged (DIRECT mode) for docker — the same
# way any docker-needing execgroup runs (decision 16).
#
#   GHCR_IMAGE     ghcr.io/<owner>/openci-tf@sha256:<digest> (digest-pinned)
#   ECR_IMAGE_TAG  the release's IMAGE_VERSION; must match the tag the
#                  installer's deploy stage waits for
#   OPENCI_TF_PROJECT  ECR repository name (default openci-tf)
#   METHOD         create (default) copies; destroy deletes the pushed tag
# ---------------------------------------------------------------------------
set -euo pipefail

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:?AWS_DEFAULT_REGION is required}}"
PROJECT="${OPENCI_TF_PROJECT:-openci-tf}"
GHCR_IMAGE="${GHCR_IMAGE:?GHCR_IMAGE is required (ghcr.io/<owner>/openci-tf@sha256:<digest>)}"
ECR_IMAGE_TAG="${ECR_IMAGE_TAG:?ECR_IMAGE_TAG is required (the release IMAGE_VERSION)}"
METHOD="${METHOD:-create}"

case "$GHCR_IMAGE" in
  ghcr.io/*@sha256:*) ;;
  *)
    echo "ERROR: GHCR_IMAGE must be a digest-pinned GHCR reference (ghcr.io/<owner>/openci-tf@sha256:...)" >&2
    exit 1
    ;;
esac

ACCT="$(aws sts get-caller-identity --query Account --output text)"
ECR_REGISTRY="${ACCT}.dkr.ecr.${REGION}.amazonaws.com"
ECR_IMAGE="${ECR_REGISTRY}/${PROJECT}:${ECR_IMAGE_TAG}"

if [ "$METHOD" = "destroy" ]; then
    # Teardown of this stage alone: drop the pushed tag. The repository itself
    # is owned by (and removed with) the installer's ecr stage. Only the exact
    # idempotent ImageNotFoundException is accepted; auth, network, and missing
    # repository failures remain loud.
    ERROR_FILE="$(mktemp)"
    trap 'rm -f "$ERROR_FILE"' EXIT
    if ! aws ecr describe-images --region "$REGION" \
        --repository-name "$PROJECT" \
        --image-ids imageTag="$ECR_IMAGE_TAG" >/dev/null 2>"$ERROR_FILE"; then
        if grep -q 'ImageNotFoundException' "$ERROR_FILE"; then
            echo "image tag ${ECR_IMAGE_TAG} already absent from ${PROJECT}"
            echo "CONFIG0_DESTROY_PRE_STATE_COUNT=0"
            echo "CONFIG0_DESTROY_POST_STATE_COUNT=0"
            exit 0
        fi
        cat "$ERROR_FILE" >&2
        exit 1
    fi
    aws ecr batch-delete-image --region "$REGION" \
        --repository-name "$PROJECT" \
        --image-ids imageTag="$ECR_IMAGE_TAG"
    echo "deleted ${ECR_IMAGE}"
    # The CLI's execgroup destroy finalizer reads these markers from the engine
    # ExecutionResult; this stage owns no generic resource row, so a successful
    # tag deletion is the zero-remaining evidence.
    echo "CONFIG0_DESTROY_PRE_STATE_COUNT=0"
    echo "CONFIG0_DESTROY_POST_STATE_COUNT=0"
    exit 0
fi

docker pull "$GHCR_IMAGE"
docker tag "$GHCR_IMAGE" "$ECR_IMAGE"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
docker push "$ECR_IMAGE"
echo "copied ${GHCR_IMAGE} -> ${ECR_IMAGE}"
