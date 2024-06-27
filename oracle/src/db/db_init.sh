#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# Install SQL*Plus
if [[ `arch` == "aarch64" ]]; then
  sudo dnf install -y oracle-release-el8 
  sudo dnf install -y oracle-instantclient19.19-basic oracle-instantclient19.19-sqlplus
else
  wget https://download.oracle.com/otn_software/linux/instantclient/2340000/oracle-instantclient-basic-23.4.0.24.05-1.el8.x86_64.rpm
  wget https://download.oracle.com/otn_software/linux/instantclient/2340000/oracle-instantclient-sqlplus-23.4.0.24.05-1.el8.x86_64.rpm
  sudo dnf install -y oracle-instantclient-basic-23.4.0.24.05-1.el8.x86_64.rpm oracle-instantclient-sqlplus-23.4.0.24.05-1.el8.x86_64.rpm
fi

# Install the tables
cat > tnsnames.ora <<EOT
DB  = $DB_URL
EOT

export TNS_ADMIN=$SCRIPT_DIR
sqlplus -L $DB_USER/$DB_PASSWORD@DB @oracle.sql $DB_PASSWORD
