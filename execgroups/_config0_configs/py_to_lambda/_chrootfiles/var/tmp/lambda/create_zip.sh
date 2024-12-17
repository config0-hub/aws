#!/bin/bash

for i in `find $VIRTUAL_ENV/$PYTHON_DIR | grep \\.pyc`
do
    rm -rf $i
done

for i in `find $VIRTUAL_ENV/$PYTHON_DIR | grep \\.swp`
do
    rm -rf $i
done

cd $VIRTUAL_ENV/$PYTHON_DIR  || exit 1
zip -r9 /tmp/$LAMBDA_PKG_NAME . || exit 1

echo ""
echo ""
echo "lambda package build for uploading is located /tmp/$LAMBDA_PKG_NAME"
echo ""
echo ""

