#!/bin/bash

export LAMBDA_PKG_NAME=${LAMBDA_PKG_NAME:=test-lambda}
export LAMBDA_PKG_DIR=${LAMBDA_PKG_DIR:=/var/tmp/package/lambda}
export S3_BUCKET=${S3_BUCKET:=test-lambda-bucket}
export DOCKER_TEMP_IMAGE=${DOCKER_TEMP_IMAGE:=temp-lambda-pkg}
export WORKING_DIR=${WORKING_DIR:=$WORKING_DIR}
export WORKING_SUBDIR=${WORKING_SUBDIR:=var/tmp/lambda}
export DOCKERFILE_LAMBDA=${DOCKERFILE_LAMBDA:=Dockerfile-to-s3}

######################################################
# Main
######################################################

cd $WORKING_DIR/$WORKING_SUBDIR

echo "######################################################"
echo "# Variables"
echo "######################################################"
echo "LAMBDA_PKG_NAME => ${LAMBDA_PKG_NAME}"
echo "S3_BUCKET => ${S3_BUCKET}"
echo "DOCKER_TEMP_IMAGE => ${DOCKER_TEMP_IMAGE}"
echo "WORKING_DIR => ${WORKING_DIR}"
echo "WORKING_SUBDIR => ${WORKING_SUBDIR}"
echo "######################################################"

docker build --build-arg pkg_name=$LAMBDA_PKG_NAME --build-arg s3_bucket=$S3_BUCKET -t $DOCKER_TEMP_IMAGE . -f $DOCKERFILE_LAMBDA || exit 9

echo "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" > .env
echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" >> .env
echo "LAMBDA_PKG_NAME=${LAMBDA_PKG_NAME}" >> .env
echo "S3_BUCKET=${S3_BUCKET}" >> .env
echo "DOCKER_TEMP_IMAGE=${DOCKER_TEMP_IMAGE}" >> .env

docker run --rm -i --env-file .env $DOCKER_TEMP_IMAGE cp ${LAMBDA_PKG_DIR}/${LAMBDA_PKG_NAME}.zip s3://${S3_BUCKET}/${LAMBDA_PKG_NAME}.zip || exit 6
rm -rf .env
