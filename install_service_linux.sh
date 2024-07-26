#!/bin/bash

case `uname` in
  Linux )
     LINUX=1
     which apk && {
        echo "Alpine"
        mkdir -p /usr/local/monitor
        \cp -f .env /usr/local/monitor
        \cp -f report.py /usr/local/monitor
        \cp -f ip.json /usr/local/monitor

        cat > /etc/local.d/monitor.start << EOF
cd /usr/local/monitor/
nohup /usr/bin/python3 /usr/local/monitor/report.py &

EOF

        chmod +x /etc/local.d/monitor.start
        rc-update add local
        rc-service local start
        }
     (which yum || which apt-get) && { 
        echo "CentOS or Debian"
        mkdir -p /usr/local/monitor
        \cp -f report.py /usr/local/monitor
        \cp -f .env /usr/local/monitor
        \cp -f ip.json /usr/local/monitor

        cat > /lib/systemd/system/monitor.service << EOF
[Unit]
Description=server monitor
After=network.target

[Service]
User=root
ExecStart=/usr/bin/python3 /usr/local/monitor/report.py
WorkingDirectory=/usr/local/monitor/
Restart=always

[Install]
WantedBy=multi-user.target

EOF
        systemctl daemon-reload
        systemctl start monitor
        systemctl enable monitor
        }
     ;;
  Darwin )
     DARWIN=1
     ;;
  * )
     # Handle AmigaOS, CPM, and modified cable modems.
     ;;
esac

