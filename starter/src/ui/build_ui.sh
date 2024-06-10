#!/bin/bash
# Build_ui.sh
#
# Compute:
# - build the code 
# - create a $ROOT/compute/ui directory with the compiled files
# - and a start.sh to start the program
# Docker:
# - build the image

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. $SCRIPT_DIR/../../env.sh -no-auto
. $BIN_DIR/build_common.sh

# XXXX
TF_VAR_deploy_type=compute
# XXXX

BUILD_DIR=$TARGET_DIR/jetui
if [ -d $BUILD_DIR ]; then
  cd $BUILD_DIR
  node_modules/grunt-cli/bin/grunt vb-clean
else
  mkdir $BUILD_DIR
  cd $BUILD_DIR
  unzip $SCRIPT_DIR/starter.zip
  npm install
fi
node_modules/grunt-cli/bin/grunt vb-process-local
exit_on_error
cd $SCRIPT_DIR

mkdir -p ui
rm -Rf ui/*
cp -r $BUILD_DIR/build/processed/webApps/starter/* ui/.

# Common Function
build_ui