#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "  CJ DROPSHIPPING FOR WHOP - ENTERPRISE AWS EC2 DEPLOYMENT"
echo "  Automated 24/7 Service Setup with Auto-Restart & Caddy HTTPS"
echo "======================================================================"

sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl debian-keyring debian-archive-keyring apt-transport-https

# Install Caddy for automatic free HTTPS & SSL
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg --yes
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update -y
sudo apt-get install -y caddy

# Clone or pull repo
TARGET_DIR="/opt/cjdropshipping-whop"
if [ -d "$TARGET_DIR" ]; then
  cd "$TARGET_DIR"
  git pull origin main
else
  sudo git clone https://github.com/takiahmed24/cjdropshipping-whop.git "$TARGET_DIR"
  sudo chown -R ubuntu:ubuntu "$TARGET_DIR"
  cd "$TARGET_DIR"
fi

# Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Write Production .env
cat << 'EOF' > "$TARGET_DIR/.env"
HOST=127.0.0.1
PORT=8090
DEBUG=False
WHOP_APP_ID=app_K7qBzRHMMJSnv7
NEXT_PUBLIC_WHOP_APP_ID=app_K7qBzRHMMJSnv7
WHOP_API_KEY=apik_Db2iiIYZncRnF_A2096732_C_89b1e1771536fa4975581d6c069c5278c737317e5cbe255fc7bb7cc3170be8
PLAN_NAME=CJdropshipping Automation
PLAN_PRICE_USD=5.00
TRIAL_DAYS=60
EOF

# Create Systemd 24/7 service
sudo bash -c "cat << 'EOF' > /etc/systemd/system/whop-cj.service
[Unit]
Description=CJ Dropshipping for Whop SaaS Bridge
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/cjdropshipping-whop
EnvironmentFile=/opt/cjdropshipping-whop/.env
ExecStart=/opt/cjdropshipping-whop/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8090
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable whop-cj
sudo systemctl restart whop-cj

# Get Public IP
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
NIP_DOMAIN="${PUBLIC_IP}.sslip.io"

# Configure Caddy for instant HTTPS on sslip.io
sudo bash -c "cat << EOF > /etc/caddy/Caddyfile
${NIP_DOMAIN} {
    reverse_proxy 127.0.0.1:8090
}
EOF"

sudo systemctl restart caddy

echo "======================================================================"
echo "  SUCCESS! CJ Dropshipping Whop Bridge is LIVE on AWS EC2!"
echo "  Live HTTPS URL: https://${NIP_DOMAIN}"
echo "======================================================================"
