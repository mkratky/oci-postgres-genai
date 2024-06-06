dnf module list postgresql
dnf module switch-to postgresql:16
dns install postgresql postgresql-server -y
dnf install postgresql-server-devel -y
postgresql-setup initdb
ls /etc/system.d
systemctl enable postgresql
systemctl start postgresql
systemctl status postgresql
su - postgres <<EOF
psql -c "alter user postgres with password 'xxxxxxx__1234'"
EOF
if [ ! -f /var/lib/pgsql/data/pg_hba.conf.orig ]; then
  cp /var/lib/pgsql/data/pg_hba.conf /var/lib/pgsql/data/pg_hba.conf.orig
fi
sed -i "s/Indent/password/" /var/lib/pgsql/data/pg_hba.conf
systemctl restart postgresql

cat > /tmp/create_user.sql <<EOF
CREATE USER postgres WITH CREATEDB CREATEROLE PASSWORD 'xxxxxxx__1234';
\du
CREATE DATABASE postgresdb OWNER postgres;
\l
EOF


su - postgres -c "psql -f /tmp/create_user.sql"
EOF

c;




sudo firewall-cmd --zone=public --add-port=5432/tcp --permanent
sudo firewall-cmd --reload

sudo dnf install git gcc redhat-rpm-config -y
cd /tmp
git clone --branch v0.7.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install # may need sudo