#!/bin/bash
set -xe

apt install -y gcc python3-dev python3-psutil python3-dotenv python3-wheel g++ python3-setuptools

pip3 install -r requirements.txt

pip3 install pyinstaller

pyinstaller --onefile report.py

cd dist
chmod +rx report
chmod +r ./*
cd ..
mv .env dist/
mv dist monitor
