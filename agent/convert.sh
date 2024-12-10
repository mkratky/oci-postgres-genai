#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR/..

oracle/convert.sh
cp -r agent/* starter/.

OLD_DIR=starter/src/terraform/old
mkdir $OLD_DIR
mv starter/src/terraform/network.tf $OLD_DIR
mv starter/src/terraform/atp.tf $OLD_DIR
mv starter/src/terraform/output.tf $OLD_DIR
mv starter/src/terraform/apigw_atp.tf $OLD_DIR

sed -i 's/TF_VAR_prefix="psql"/TF_VAR_prefix="agent"/' starter/env.sh
sed -i 's/TF_VAR_prefix="db23ai"/TF_VAR_prefix="agent"/' starter/env.sh