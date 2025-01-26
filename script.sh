#!/bin/bash
apt-get update
apt-get install -y python3-pip python3-venv nginx
# Clone the GitHub repository
apt-get install -y git
git clone https://github.com/karimhozaien/SwiftAid /opt/swiftaid
cd /opt/swiftaid/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Install Gunicorn
pip install gunicorn
# Create a Gunicorn systemd service
cat <<EOF > /etc/systemd/system/swiftaid.service
[Unit]
Description=Gunicorn instance to serve SwiftAid Flask App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/swiftaid/backend
Environment="PATH=/opt/swiftaid/backend/venv/bin"
ExecStart=/opt/swiftaid/backend/venv/bin/gunicorn --workers 3 --bind unix:/opt/swiftaid/backend/swiftaid.sock app:app

[Install]
WantedBy=multi-user.target
EOF
# Start and enable Gunicorn service
systemctl start swiftaid
systemctl enable swiftaid
# Configure Nginx
cat <<EOF > /etc/nginx/sites-available/swiftaid
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://unix:/opt/swiftaid/backend/swiftaid.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
ln -s /etc/nginx/sites-available/swiftaid /etc/nginx/sites-enabled
nginx -t
systemctl restart nginx

