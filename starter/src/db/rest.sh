#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

. ./env.sh

python3.9 rest.py 2>&1 | tee rest.log

# Ex: curl "http://$BASTION_IP:8080/query?type=text&question=jazz"
