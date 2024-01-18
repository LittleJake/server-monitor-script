#!/bin/bash

mkdir -p /usr/local/monitor
\cp -f report.py /usr/local/monitor
\cp -f .env /usr/local/monitor

cat > /lib/systemd/system/monitor.service << EOF
[Unit]
Description=monitor
After=network.target

[Service]
User=root
ExecStart=/usr/bin/python3 /usr/local/monitor/r.py
Restart=always

[Install]
WantedBy=multi-user.target

EOF

systemctl daemon-reload
systemctl start monitor
systemctl enable monitor

