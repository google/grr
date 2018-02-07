#!/bin/bash
set -e

WINDOWS_INSTALLER_UPLOAD_URL=$(curl http://metadata.google.internal/computeMetadata/v1/project/attributes//windows_installer_upload_url -H "Metadata-Flavor: Google")
LINUX_INSTALLER_UPLOAD_URL=$(curl http://metadata.google.internal/computeMetadata/v1/project/attributes//linux_installer_upload_url -H "Metadata-Flavor: Google")

apt-get -y update
wget "https://storage.googleapis.com/releases.grr-response.com/grr-server_3.2.1-1_amd64.deb"
env DEBIAN_FRONTEND=noninteractive apt install -y ./grr-server_3.2.1-1_amd64.deb
service grr-server stop

apt-get -y install nginx
cd /etc/nginx
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=${server_host}" -keyout /etc/nginx/cert.key -out /etc/nginx/cert.crt

cat <<"EOF" > /etc/nginx/sites-enabled/default
server {
    listen 80;
    return 301 https://$$host$$request_uri;
}

server {
    listen 443;
    server_name ${server_host};

    ssl_certificate           /etc/nginx/cert.crt;
    ssl_certificate_key       /etc/nginx/cert.key;

    ssl on;
    ssl_session_cache  builtin:1000  shared:SSL:10m;
    ssl_protocols  TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!eNULL:!EXPORT:!CAMELLIA:!DES:!MD5:!PSK:!RC4;
    ssl_prefer_server_ciphers on;

    access_log            /var/log/nginx/grr.access.log;

    location / {

      proxy_set_header        Host $$host;
      proxy_set_header        X-Real-IP $$remote_addr;
      proxy_set_header        X-Forwarded-For $$proxy_add_x_forwarded_for;
      proxy_set_header        X-Forwarded-Proto $$scheme;

      # Fix the 'It appears that your reverse proxy set up is broken' error.
      proxy_pass          http://localhost:8000;
      proxy_read_timeout  180;

      proxy_redirect      http://localhost:8000 https://${server_host};
    }
}
EOF
sudo service nginx restart


cat << EOF > /etc/grr/server.local.yaml
Datastore.implementation: MySQLAdvancedDataStore
Mysql.host: ${mysql_host}
Mysql.port: 3306
Mysql.database_name: grr-db
Mysql.database_username: grr
Mysql.database_password: grrpassword

Client.server_urls: http://${server_host}:8080/
Frontend.bind_port: 8080
AdminUI.url: https://${server_host}:8000
AdminUI.port: 8000
Logging.domain: localhost
Monitoring.alert_email: grr-monitoring@localhost
Monitoring.emergency_access_email: grr-emergency@localhost
Rekall.enabled: 'False'
Server.initialized: 'True'

Client.foreman_check_frequency: 30
Client.poll_max: 5
EOF

grr_config_updater generate_keys
grr_config_updater repack_clients

grr_config_updater add_user --password admin admin

service grr-server start

curl -X PUT -T - "$$WINDOWS_INSTALLER_UPLOAD_URL" < /usr/share/grr-server/executables/installers/GRR_3.2.1.1_amd64.exe
curl -X PUT -T - "$$LINUX_INSTALLER_UPLOAD_URL" < /usr/share/grr-server/executables/installers/grr_3.2.1.1_amd64.deb
