#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  🚀 Code Devil Bot - VPS Auto Deployment"
echo "=========================================="

# 1. Update system & install dependencies
echo "[1/4] Installing system dependencies..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git ffmpeg build-essential

# 2. Virtual Environment setup
echo "[2/4] Setting up Python virtual environment..."
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Create systemd service for 24/7 background running
echo "[3/4] Configuring 24/7 systemd service..."

cat << EOF > /etc/systemd/system/telegram-bot.service
[Unit]
Description=Code Devil Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python main.py
Restart=always
RestartSec=5
KillMode=process

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable telegram-bot

# 4. Check .env and start service
echo "[4/4] Starting bot service..."
if [ ! -f "$DIR/.env" ]; then
    echo "⚠️ .env file not found in $DIR."
    echo "Please create .env file and then run: systemctl start telegram-bot"
else
    systemctl restart telegram-bot
    echo "=========================================="
    echo "🎉 Deployment Complete! Bot is LIVE 24/7"
    echo "=========================================="
    systemctl status telegram-bot --no-pager
fi
