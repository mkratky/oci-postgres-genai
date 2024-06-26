#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR/..

rm starter/src/db/*
rm starter/src/terraform/psql.tf
cp -r oracle/* starter/.
sed -i 's/TF_VAR_db_type="psql"/TF_VAR_db_type="database"/' starter/env.sh