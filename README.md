server-monitor-script
=======

<img alt="Apache 2.0" src="https://img.shields.io/github/license/LittleJake/server-monitor-script?style=for-the-badge"> <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/LittleJake/server-monitor-script?style=for-the-badge">

<img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white"> <img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black"> <img src="https://img.shields.io/badge/python3-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54">

[Server Monitor](https://github.com/LittleJake/server-monitor/)的探针节点脚本，支持多种系统。

数据上报至Redis服务器，Linux、Windows已通过测试。

可注册使用免费Redis服务器：[redislab](https://redis.com/)、[aiven.io](https://console.aiven.io/)。

### 安装


#### Docker

```bash
git clone https://github.com/LittleJake/server-monitor-script/

# 编辑.env.example文件保存为.env文件
cp .env.example .env
vim .env

docker build -t server-monitor-script:latest ./
docker run -v /:/rootfs:ro -d server-monitor-script:latest monitor

```

#### Linux

```bash
git clone https://github.com/LittleJake/server-monitor-script/

pip3 install -r requirements.txt

# 编辑.env.example文件保存为.env文件
cp .env.example .env
vim .env

# 安装服务CentOS/Debian/Ubuntu
bash install_service_linux.sh

```

#### Windows

```cmd
git clone https://github.com/LittleJake/server-monitor-script/

pip3 install -r requirements.txt
# 编辑.env.example文件保存为.env文件
copy .env.example .env
notepad .env

# 运行服务
python3 report.py

```


### Sponsors

Thanks for the amazing VM server provided by [DartNode](https://dartnode.com?via=1).

 <a href="https://dartnode.com?via=1"><img src="https://raw.githubusercontent.com/LittleJake/LittleJake/master/images/dartnode.png" width="150"></a>

Thanks for the open source project license provided by [JetBrains](https://www.jetbrains.com/).

 <a href="https://www.jetbrains.com/"><img src="https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.png" width="150" alt="JetBrains Logo (Main) logo."></a>
