#!/usr/bin/env bash
set -euo pipefail

USER_NAME="ec2-user"
HOME_DIR="/home/${USER_NAME}"
STATE_DIR="${HOME_DIR}/.openclaw"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/7] Stopping services (ignore errors if missing)..."
sudo systemctl stop openclaw-gateway.service 2>/dev/null || true
sudo systemctl stop openclaw.service 2>/dev/null || true
sudo systemctl stop socat-openclaw.service 2>/dev/null || true

echo "[2/7] Snapshot current state..."
TS="$(date +%Y%m%d-%H%M%S)"
if [ -d "${STATE_DIR}" ]; then
  sudo tar -C "${HOME_DIR}" -czf "${HOME_DIR}/openclaw-snapshot-${TS}.tgz" .openclaw || true
  echo "  Snapshot saved: ${HOME_DIR}/openclaw-snapshot-${TS}.tgz"
fi

echo "[3/7] Restore ~/.openclaw from repo..."
sudo rm -rf "${STATE_DIR}"
sudo mkdir -p "${STATE_DIR}"
sudo rsync -a --delete "${REPO_DIR}/" "${STATE_DIR}/" \
  --exclude ".git" \
  --exclude "systemd" \
  --exclude "restore.sh" \
  --exclude "install.sh" \
  --exclude "README.md" \
  --exclude "*.log" || true
sudo chown -R "${USER_NAME}:${USER_NAME}" "${STATE_DIR}"

echo "[4/7] Install systemd unit(s)..."
if [ -f "${REPO_DIR}/systemd/openclaw-gateway.service" ]; then
  sudo install -m 0644 "${REPO_DIR}/systemd/openclaw-gateway.service" /etc/systemd/system/openclaw-gateway.service
fi
if [ -f "${REPO_DIR}/systemd/openclaw.service" ]; then
  sudo install -m 0644 "${REPO_DIR}/systemd/openclaw.service" /etc/systemd/system/openclaw.service
fi

echo "[5/7] systemd reload..."
sudo systemctl daemon-reload
sudo systemctl reset-failed || true

echo "[6/7] Start gateway..."
sudo systemctl enable --now openclaw-gateway.service

echo "[7/7] Verify port 18789..."
if sudo ss -ltnp | grep -q ":18789"; then
  echo "✅ Listening on 18789"
  sudo ss -ltnp | grep ":18789" || true
else
  echo "❌ Not listening on 18789"
  echo "Logs:"
  sudo journalctl -u openclaw-gateway.service -b --no-pager -n 80 || true
  exit 1
fi
