#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR/..

if [ "$1" = "" ];
  echo "ERROR: give TF_VAR_genai_agent_datasource_ocid value as parameter"
  exit
fi

oracle/convert.sh
cp -r agent/* starter/.

echo "export TF_VAR_genai_agent_datasource_ocid=$1" > starter/src/compute/app/ingest.sh