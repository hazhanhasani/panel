#!/bin/bash

SERVICE_NAME="bluepanel"
SERVICE_DESCRIPTION="BluePanel Service"
SERVICE_DOCUMENTATION="https://github.com/hazhanhasani/panel"
MAIN_PY_PATH="$PWD/main.py"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=$SERVICE_DESCRIPTION
Documentation=$SERVICE_DOCUMENTATION
After=network.target nss-lookup.target

[Service]
ExecStart=$PWD/.venv/bin/python3 $MAIN_PY_PATH
Restart=on-failure
WorkingDirectory=$PWD

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo "BluePanel service file created at: $SERVICE_FILE"
