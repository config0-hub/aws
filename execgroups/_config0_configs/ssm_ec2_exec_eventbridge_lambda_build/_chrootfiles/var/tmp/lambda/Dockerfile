# ---------------------------------------------------------------------------
# One shared, parameterized Dockerfile that builds a Lambda deployment zip for
# any one of the three handlers. Mirrors the config0 authoring
# py_to_lambda-codebuild Dockerfile: a build stage that pip-installs the
# per-lambda requirements, lays the handler source on top, and zips the whole
# package; then a tiny export stage that carries the zip at a fixed path so
# docker-to-lambda.sh can `docker cp` it out (the codebuild flow does the same).
#
# The zip is built with handler.py at its ROOT, so the Lambda handler stays
# handler.handler.
#
# Build args:
#   python_version - runtime image tag (default 3.12, matches the aws_lambda_function runtime)
#   pkg_name       - output zip basename (<pkg_name>.zip)
#   src_dir        - handler source dir, relative to the build context (lambdas/)
# ---------------------------------------------------------------------------

ARG python_version=3.12

# ref nexus update
FROM nexus:8083/docker/library/python:${python_version} AS build

ARG pkg_name=PleaseSetPkgName
ARG src_dir=PleaseSetSrcDir
ARG build_dir=/build

ENV PKG_NAME=$pkg_name
ENV BUILD_DIR=$build_dir

RUN apt-get update && apt-get install -y --no-install-recommends zip && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p $BUILD_DIR/package

# Per-lambda dependencies (may be empty — these handlers use only boto3 from the
# runtime — but the flow supports future deps).
COPY $src_dir/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt -t $BUILD_DIR/package

# Handler source on top, at the package root.
COPY $src_dir/ $BUILD_DIR/package/

# Zip the package contents (handler.py at zip root). Drop bytecode caches.
RUN cd $BUILD_DIR/package && \
    zip -r9 $BUILD_DIR/$PKG_NAME.zip . -x '*__pycache__*' '*.pyc' && \
    echo "Lambda package built: $BUILD_DIR/$PKG_NAME.zip"

# Export stage: a minimal image whose only job is to hold the zip at a fixed
# path for `docker cp` (standalone) — the codebuild flow also cp's from here.
# ref nexus update
FROM nexus:8083/docker/library/alpine:3.20 AS export

ARG pkg_name=PleaseSetPkgName
ARG build_dir=/build

COPY --from=build $build_dir/$pkg_name.zip /lambda.zip
