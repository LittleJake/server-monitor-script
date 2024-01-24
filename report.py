import sys
import json
import math
import re
import redis
import logging
import time
import requests
import psutil
import uuid
import os
import cpuinfo
import distro
import platform
from datetime import timedelta
from dotenv import load_dotenv, find_dotenv

# get .env location for pyinstaller
extDataDir = os.getcwd()
if getattr(sys, 'frozen', False):
    extDataDir = sys._MEIPASS
load_dotenv(dotenv_path=os.path.join(extDataDir, '.env'))


HOST = os.getenv("HOST", "127.0.0.1")
PORT = os.getenv("PORT", "6379")
PASSWORD = os.getenv("PASSWORD", "")
SSL = os.getenv("SSL", 'False').lower() in ('true', '1', 't')
IPV4_API = os.getenv('IPV4_API', "http://v4.ipv6-test.com/api/myip.php")
IPV6_API = os.getenv('IPV6_API', "http://v6.ipv6-test.com/api/myip.php")
IP_API = os.getenv('IP_API', "http://ip-api.com/json?fields=country,countryCode")
REPORT_INTEVAL = int(os.getenv('REPORT_INTEVAL', '60'))
DATA_TIMEOUT = int(os.getenv('DATA_TIMEOUT', '259200'))
RETENTION_TIME = int(os.getenv('RETENTION_TIME', '86400'))
DISK_EXCLUDE = os.getenv('DISK_EXCLUDE','/run,/sys,/boot,/dev,/proc,/var/lib').split(",")
DISK_FS_EXCLUDE = os.getenv('DISK_FS_EXCLUDE', 'tmpfs,overlay').split(",")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
UUID = str(uuid.uuid4()).replace("-", "")
IPV4 = None
IPV6 = None
COUNTRY = None
conn = redis.Redis(host=HOST, password=PASSWORD, port=PORT, ssl=SSL, retry_on_timeout=10)
TIME = math.floor(time.time())
NET_FORMER = psutil.net_io_counters()
CPU_INFO = cpuinfo.get_cpu_info()

def get_network():
    global NET_FORMER
    net_temp = psutil.net_io_counters()

    network = {'RX': {
        'bytes': net_temp.bytes_recv - NET_FORMER.bytes_recv,
        'packets': net_temp.packets_recv - NET_FORMER.packets_recv,
    }, 'TX': {
        'bytes': net_temp.bytes_sent - NET_FORMER.bytes_sent,
        'packets': net_temp.packets_sent - NET_FORMER.packets_sent,
    }}

    NET_FORMER = net_temp
    return network


def get_process_num():
    return len(psutil.pids())


def get_cpu_name():
    return CPU_INFO['brand_raw']

def get_load_average():
    try:
        avg = psutil.getloadavg()
    except: return "Not support"
    return "%.2f, %.2f, %.2f" % avg

def get_cpu_core():
    # core modelname mhz'''
    return str(psutil.cpu_count())


def get_temp():
    # thermal temp
    result = {}
    try:
        for sensor_type, sensors in psutil.sensors_temperatures().items():
            for sensor in sensors:
                result[sensor_type+":"+sensor.label] = sensor.current
    except: 
        pass
    return result

def get_battery():
    # battery temp
    result = {}
    try:
        result["percent"] = psutil.sensors_battery().percent
    except:
        pass
    return result

def get_mem_info():
    info = {'Mem': {
        'total': '%.2f' % (psutil.virtual_memory().total*1.0/1048576),
        'used': '%.2f' % (psutil.virtual_memory().used*1.0/1048576),
        'free': '%.2f' % (psutil.virtual_memory().free*1.0/1048576),
        'percent': psutil.virtual_memory().percent,
    }, 'Swap': {
        'total': '%.2f' % (psutil.swap_memory().total*1.0/1048576),
        'used': '%.2f' % (psutil.swap_memory().used*1.0/1048576),
        'free': '%.2f' % (psutil.swap_memory().free*1.0/1048576),
        'percent': psutil.swap_memory().percent,
    }}
    return info


def get_sys_version():
    # System and version'''
    if distro.name() != "":
        return " ".join([distro.name(), distro.version(), distro.codename()])
    else:
        return " ".join([platform.system(), platform.release()])


def get_disk_partitions():
    parts = psutil.disk_partitions(True)
    result = []
    for part in parts:
        result.append(part)
        for i in DISK_EXCLUDE:
            if part.mountpoint.find(i) != -1 or part.fstype in DISK_FS_EXCLUDE:
                result.remove(part)
                break
                
    return result


def get_disk_info():
    disks = {}

    for partition in get_disk_partitions():
        disk = psutil.disk_usage(partition.mountpoint)
        disks[partition.mountpoint] = {
            'total': '%.2f' % (disk.total*1.0/1048576),
            'used': '%.2f' % (disk.used*1.0/1048576),
            'free':  '%.2f' % (disk.free*1.0/1048576),
            'percent': disk.percent
        }

    return disks


def get_ipv4():
    # interface ipv4'''
    global IPV4
    if IPV4 is None:
        i = 5
        while i > 0:
            try:
                resp = requests.get(url=IPV4_API, timeout=5)
                if resp.status_code == 200:
                    IPV4 = resp.text
                    return IPV4
            except:
                i = i - 1

        return "None"
    else:
        return IPV4


def get_ipv6():
    # interface ipv6
    global IPV6
    if IPV6 is None:
        i = 5
        while i > 0:
            try:
                resp = requests.get(url=IPV6_API, timeout=5)
                if resp.status_code == 200:
                    return resp.text
            except:
                i = i - 1

        return "None"
    else:
        return IPV6


def get_country():
    # interface ipv6
    global COUNTRY
    if COUNTRY is None:
        i = 5
        while i > 0:
            try:
                resp = requests.get(url=IP_API, timeout=5)
                if resp.status_code == 200:
                    j = resp.json()
                    COUNTRY = (j["country"], j["countryCode"])
                    return COUNTRY
            except:
                i = i - 1

        return ("None", "None")
    else:
        return COUNTRY


def get_connections():
    return len(psutil.net_connections())


def get_uptime():
    t = int(time.time() - psutil.boot_time())
    delta = timedelta(seconds=t)
    return str(delta)

def get_cpu_freq():
    return CPU_INFO.get('hz_advertised_friendly', "%.2f Ghz" % (psutil.cpu_freq().max / 1000))


def get_load():
    return dict(psutil.cpu_times_percent()._asdict())


def get_aggregate_stat_json():
    return json.dumps(get_aggregate_stat())


def get_aggregate_stat():
    info = {
        'Disk': get_disk_info(),
        'Memory': get_mem_info(),
        'Load': get_load(),
        'Network': get_network(),
        'Thermal': get_temp(),
        'Battery': get_battery(),
    }
    logging.debug(info)
    return info


def report_once():
    """ip"""
    global IP, TIME
    logging.info("Reporting...")
    IP = get_ipv4()
    TIME = time.time()
    COUNTRY = get_country()
    logging.debug("{}x {} @{}".format(get_cpu_core(), CPU_INFO.get('brand_raw', CPU_INFO.get('arch_string_raw', 'Unknown')), get_cpu_freq()))
    logging.debug(get_sys_version())
    logging.debug(re.sub("[0-9]*\.[0-9]*\.[0-9]*", "*.*.*", get_ipv4()))
    logging.debug(re.sub("[a-zA-Z0-9]*:", "*:", get_ipv6()))
    logging.debug(get_uptime())
    logging.debug(get_connections())
    logging.debug(get_process_num())
    logging.debug(get_load_average())
    logging.debug(TIME)
    logging.debug(COUNTRY[0])
    logging.debug(COUNTRY[1])
    logging.debug("D: %.2f GB / U: %.2f GB" % (NET_FORMER.bytes_recv/1073741824, NET_FORMER.bytes_sent/1073741824))

    info = {
        "CPU": "{}x {} @{}".format(get_cpu_core(), CPU_INFO.get('brand_raw', CPU_INFO.get('arch_string_raw', 'Unknown')), get_cpu_freq()),
        "System Version": get_sys_version(),
        "IPV4": re.sub("[0-9]*\.[0-9]*\.[0-9]*", "*.*.*", get_ipv4()),
        "IPV6": re.sub("[a-zA-Z0-9]*:", "*:", get_ipv6()),
        'Uptime': get_uptime(),
        'Connection': get_connections(),
        'Process': get_process_num(),
        'Load Average': get_load_average(),
        "Update Time": TIME,
        "Country": COUNTRY[0],
        "Country Code": "CN" if COUNTRY[1] in ("TW", "HK", "MO") else COUNTRY[1],
        "Throughput": "D: %.2f GB / U: %.2f GB" % (NET_FORMER.bytes_recv/1073741824, NET_FORMER.bytes_sent/1073741824),
    }
    

    with conn.pipeline(transaction=False) as pipeline:
        pipeline.hset(name="system_monitor:hashes", mapping={UUID: IP})
        pipeline.hset(name="system_monitor:info:" + UUID, mapping=info)
        pipeline.zadd("system_monitor:collection:" + UUID, {get_aggregate_stat_json(): TIME})
        pipeline.zremrangebyscore("system_monitor:collection:" + UUID, 0, TIME - RETENTION_TIME)
        pipeline.expire("system_monitor:nodes", DATA_TIMEOUT)
        pipeline.expire("system_monitor:hashes", DATA_TIMEOUT)
        pipeline.expire("system_monitor:info:" + UUID, DATA_TIMEOUT)
        pipeline.expire("system_monitor:collection:" + UUID, DATA_TIMEOUT)
        pipeline.execute()

    logging.info("Finish Reporting!")


if os.path.isfile('.uuid'):
    with open('.uuid', 'r') as fp:
        UUID = fp.read().strip()
else:
    with open('.uuid', 'w') as fp:
        fp.write(UUID)


while True:
    try:
        report_once()
    except Exception as e:
        logging.error(e)
    time.sleep(REPORT_INTEVAL)
