#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

export DB_PASSWORD

# Install APEX and DBMS_CLOUD
sudo su - root -c "$SCRIPT_DIR/root_install_apex.sh"
sudo su - oracle -c "$SCRIPT_DIR/oracle_install_apex.sh"
