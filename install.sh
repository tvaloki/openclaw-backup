#!/usr/bin/env bash
set -euo pipefail

echo "Installing systemd unit(s) from repo..."
sudo install -m 0644 systemd/openclaw-gateway.service /etc/systemd/system/openclaw-gateway.service

if [ -f systemd/openclaw.service ]; then
  sudo install -m 0644 systemd/openclaw.service /etc/systemd/system/openclaw.service
fi

sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-gateway.service

echo "Done. Status:"
sudo systemctl status openclaw-gateway.service --no-pager -l || true
