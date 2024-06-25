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

UI_NAME=search_ui
BUILD_DIR=$TARGET_DIR/jetui
sha1sum $UI_NAME.zip > $TARGET_DIR/jetui.sha1
if [ -d $BUILD_DIR ]; then
  cd $BUILD_DIR
  node_modules/grunt-cli/bin/grunt vb-clean
else
  mkdir $BUILD_DIR
  cd $BUILD_DIR
  unzip $SCRIPT_DIR/$UI_NAME.zip
  cp $TARGET_DIR/jetui.sha1 $BUILD_DIR/.
  npm install
fi

# node_modules/grunt-cli/bin/grunt vb-process-local
# If there is the error: Fatal error: Missing mandatory component exchange URL, please add "url:ce"
# See: Component exchange login (static value), see https://docs.oracle.com/en/cloud/paas/app-builder-cloud/abcag/manage-your-component-exchange.html#GUID-44796BE5-C613-497F-B1F5-437E3AC0EC05 
sed -i 's/const REST_SERVER =.*$/const REST_SERVER = ""/' webApps/search_ui/flows/simple/pages/input-search-page-chains/searchActionJS.js
node_modules/grunt-cli/bin/grunt vb-process-local  --url:ce=https://devinstance4wd8us2-wd4devcs8us2.uscom-central-1.oraclecloud.com/profile/devinstance4wd8us2-wd4devcs8us2/s/devinstance4wd8us2-wd4devcs8us2_compcatalog_3461/compcatalog/0.2.0 --username:ce=comp.catalog --password:ce="bXwphh6RMFjn#g"

exit_on_error
cd $SCRIPT_DIR

mkdir -p ui
rm -Rf ui/*
cp -r $BUILD_DIR/build/processed/webApps/$UI_NAME/* ui/.

# Common Function
build_ui

