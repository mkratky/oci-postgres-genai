#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# Install PostgreSQL client
sudo yum -y install postgresql 
export PGPASSWORD=$DB_PASSWORD
psql -h $DB_URL -d postgres -U $DB_USER -f psql.sql

# Python Server
sudo yum -y install postgresql-devel
sudo dnf install -y python39 python39-devel
sudo pip3.9 install pip --upgrade
sudo pip3.9 install -r requirements.txt

# Store the db_connection in the start.sh
CONFIG_FILE=start.sh
sed -i "s/##DB_USER##/$DB_USER/" $CONFIG_FILE
sed -i "s/##DB_PASSWORD##/$DB_PASSWORD/" $CONFIG_FILE
sed -i "s/##DB_URL##/$DB_URL/" $CONFIG_FILE

# Create an APP service
APP_DIR=db
cat > /tmp/$APP_DIR.service << EOT
[Unit]
Description=App
After=network.target

[Service]
Type=simple
ExecStart=/home/opc/$APP_DIR/start.sh
TimeoutStartSec=0
User=opc

[Install]
WantedBy=default.target
EOT

sudo cp /tmp/$APP_DIR.service /etc/systemd/system
sudo chmod 664 /etc/systemd/system/$APP_DIR.service
sudo systemctl daemon-reload
sudo systemctl enable $APP_DIR.service
sudo systemctl restart $APP_DIR.service

# Firewalld
sudo firewall-cmd --zone=public --add-port=80/tcp --permanent
sudo firewall-cmd --zone=public --add-port=443/tcp --permanent
sudo firewall-cmd --zone=public --add-port=8080/tcp --permanent
sudo firewall-cmd --reload

