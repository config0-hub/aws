# Builds one Lambda deployment zip inside the engine's CodeBuild run.
# docker-to-lambda.sh builds this image, then copies
# $SHARE_DIR/$LAMBDA_PKG_DIR/$LAMBDA_PKG_NAME.zip out of it and uploads the
# zip to S3 for the aws_lambda stack. Two stages: install the execgroup's
# pinned requirements into site-packages, then lay the handler source
# (src.tar.gz) over them and zip the result.
ARG python_release=3.11
ARG python_version=3.11

FROM public.ecr.aws/docker/library/python:${python_version} AS build

ARG python_release=3.11
ARG share_dir=/var/tmp/share

ENV PYTHON_RELEASE=$python_release
ENV SHARE_DIR=$share_dir

RUN mkdir -p $SHARE_DIR

RUN /bin/bash -c "cd $SHARE_DIR && \
    python3 -m venv $SHARE_DIR/venv && \
    source $SHARE_DIR/venv/bin/activate && \
    pip install --upgrade pip"

COPY requirements.txt /tmp/requirements.txt

WORKDIR $SHARE_DIR/venv/lib/python${PYTHON_RELEASE}/site-packages

# ponytail: wheels cover every pinned requirement on linux/amd64 for the
# supported Lambda Python releases, so no compiler or Rust toolchain is
# installed; add build-essential and rustup here if a pin ever has no wheel.
RUN /bin/bash -c "source $SHARE_DIR/venv/bin/activate && \
    pip3 install --only-binary=:all: -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt"

RUN mv $SHARE_DIR/venv/lib/python${PYTHON_RELEASE}/site-packages $SHARE_DIR/app

# the packaging container: the zip is copied out of it by docker-to-lambda.sh
FROM public.ecr.aws/docker/library/alpine:3.18.4

ARG pkg_name=PleaseSetPkgName
ARG share_dir=/var/tmp/share
ARG lambda_pkg_dir=package/lambda

ENV SHARE_DIR=$share_dir
ENV LAMBDA_PKG_NAME=$pkg_name
ENV LAMBDA_PKG_DIR=$lambda_pkg_dir

RUN apk add --no-cache zip tar gzip && \
    rm -rf /var/cache/apk/*

RUN mkdir -p $SHARE_DIR/$LAMBDA_PKG_DIR

COPY --from=build $SHARE_DIR/app $SHARE_DIR/app
# the handler source of the Lambda execgroup laid down beside this file
ADD src.tar.gz $SHARE_DIR/app
RUN chown -R root:root $SHARE_DIR/app

RUN cd $SHARE_DIR/app && \
    zip -q -r9 $SHARE_DIR/$LAMBDA_PKG_DIR/$LAMBDA_PKG_NAME . && \
    echo "Lambda package found here: $SHARE_DIR/$LAMBDA_PKG_DIR/$LAMBDA_PKG_NAME.zip"
