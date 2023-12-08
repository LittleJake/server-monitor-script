#!/bin/bash
set -xe

apk upgrade -U

apk del py3-packaging
apk add gcc python3-dev py3-psutil py3-wheel g++ build-base linux-headers zlib-dev cmake make autoconf automake libtool
pip3 install -r requirements.txt
pip3 install pyinstaller==5.13.2

pyinstaller --onefile report.py

cd build
chmod +rx report
chmod +r ./*
cd ..
mv build monitor
