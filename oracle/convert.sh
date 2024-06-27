#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR/..

rm starter/src/db/*
rm starter/src/terraform/psql.tf
cp -r oracle/* starter/.

sed -i 's/TF_VAR_db_type="psql"/TF_VAR_db_type="database"/' starter/env.sh
sed -i 's/TF_VAR_prefix="psql"/TF_VAR_prefix="db23ai"/' starter/env.sh
sed -i 's/TF_VAR_db_user="postgres"/TF_VAR_db_user="system"/' starter/env.sh
sed -i 's/POSTGRES/DB23ai/' starter/src/compute/app/requirements.txt
sed -i 's/psycopg2-binary/oracledb/' starter/src/compute/app/requirements.txt
sed -i '/searchActionJS.js/a \
sed -i "s/PostgreSQL/Oracle DB 23ai/" webApps/search_ui/flows/simple/pages/input-search-page.html \
' starter/src/ui/build_ui.sh
