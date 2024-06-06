#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

. ./env.sh

python3.9 search_ingestion.py 2>&1 | tee search_ingestion.log


