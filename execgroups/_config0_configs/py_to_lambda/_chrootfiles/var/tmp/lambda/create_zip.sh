#!/bin/bash

# Remove all .pyc files from the virtual environment's Python directory
for i in $(find $VIRTUAL_ENV/$PYTHON_DIR | grep \\.pyc); do
    rm -rf $i
done

# Remove all .swp files (Vim swap files) from the virtual environment's Python directory
for i in $(find $VIRTUAL_ENV/$PYTHON_DIR | grep \\.swp); do
    rm -rf $i
done

# Change to the virtual environment's Python directory
# Exit with an error if the directory doesn't exist
cd $VIRTUAL_ENV/$PYTHON_DIR || exit 1

# Create a ZIP archive of the directory and save it to /tmp
# Exit with an error if the zip command fails
zip -r9 /tmp/$LAMBDA_PKG_NAME . || exit 1

# Print a message indicating the location of the Lambda package
echo ""
echo ""
echo "Lambda package build for uploading is located at /tmp/$LAMBDA_PKG_NAME"
echo ""
echo ""