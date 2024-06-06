# Install PostgreSQL 16
# To run with root

dnf module list postgresql
dnf module switch-to postgresql:16 -y
dnf install postgresql postgresql-server -y
dnf install postgresql-server-devel -y --allowerasing

# Configure it 
postgresql-setup initdb
systemctl enable postgresql
systemctl start postgresql
systemctl status postgresql

# Change the posgress user password
su - postgres <<EOF
psql -c "alter user postgres with password '${DB_PASSWORD}'"
EOF

# Change the indentification method from Indent to password
if [ ! -f /var/lib/pgsql/data/pg_hba.conf.orig ]; then
  cp /var/lib/pgsql/data/pg_hba.conf /var/lib/pgsql/data/pg_hba.conf.orig
fi
sed -i "sg/ident/password/g" /var/lib/pgsql/data/pg_hba.conf

firewall-cmd --zone=public --add-port=5432/tcp --permanent
firewall-cmd --reload

# Install pgvector
dnf install git gcc redhat-rpm-config -y
cd /tmp
git clone --branch v0.7.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install 

systemctl restart postgresql