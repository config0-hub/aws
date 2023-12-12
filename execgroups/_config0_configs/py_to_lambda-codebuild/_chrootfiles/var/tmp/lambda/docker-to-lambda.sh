#!/bin/bash

export DOCKER_TEMP_IMAGE=${DOCKER_TEMP_IMAGE:=temp-lambda-pkg}
export PYTHON_VERSION=${PYTHON_VERSION:=3.8}

export MAJOR_VERSION=`echo $PYTHON_VERSION | cut -d "." -f 1`
export MINOR_VERSION=`echo $PYTHON_VERSION | cut -d "." -f 2`
export PYTHON_RELEASE="${MAJOR_VERSION}.${MINOR_VERSION}"

export SHARE_DIR=${SHARE_DIR:=/var/tmp/share}
export LAMBDA_PKG_NAME=${LAMBDA_PKG_NAME:=test-lambda}
export LAMBDA_PKG_DIR=${LAMBDA_PKG_DIR:=package/lambda}
export S3_BUCKET=${S3_BUCKET:=test-lambda-bucket}
export DOCKERFILE_LAMBDA=${DOCKERFILE_LAMBDA:=Dockerfile}

######################################################
# Main
######################################################

echo "######################################################"
echo "# Variables"
echo "######################################################"
echo "LAMBDA_PKG_NAME => ${LAMBDA_PKG_NAME}"
echo "S3_BUCKET => ${S3_BUCKET}"
echo "DOCKER_TEMP_IMAGE => ${DOCKER_TEMP_IMAGE}"
echo "######################################################"

docker build --build-arg pkg_name=$LAMBDA_PKG_NAME \
             --build-arg s3_bucket=$S3_BUCKET \
             --build-arg python_release=$PYTHON_RELEASE \
             --build-arg python_version=$PYTHON_VERSION \
             --build-arg share_dir=$SHARE_DIR \
             --build-arg lambda_pkg_dir=$LAMBDA_PKG_DIR \
             -t $DOCKER_TEMP_IMAGE . \
             -f $DOCKERFILE_LAMBDA || exit 9

echo "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" > .env
echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" >> .env
echo "AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN" >> .env
echo "LAMBDA_PKG_NAME=${LAMBDA_PKG_NAME}" >> .env
echo "S3_BUCKET=${S3_BUCKET}" >> .env
echo "DOCKER_TEMP_IMAGE=${DOCKER_TEMP_IMAGE}" >> .env

docker run --rm -i --env-file .env $DOCKER_TEMP_IMAGE cp ${SHARE_DIR}/${LAMBDA_PKG_DIR}/${LAMBDA_PKG_NAME}.zip s3://${S3_BUCKET}/${LAMBDA_PKG_NAME}.zip || exit 6
rm -rf .env
