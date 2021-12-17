import hashlib
import json
import math
import re
import redis
import subprocess
import time
import requests
import psutil
import uuid

HOST = "redis-host"
PORT = "redis-port"
PASSWORD = "redis-password"
SALT = "redis-salt"
UUID = str(uuid.uuid4()).replace("-", "")
IP = "0.0.0.0"
TIME = math.floor(time.time())
TIMEOUT = 259200
TIME_PERIOD = 86400
DISK_EXCLUDE = ['/run', '/sys', '/boot', '/dev', '/proc', '/gdrive', '/var/lib/']

conn = redis.Redis(host=HOST, password=PASSWORD, port=PORT, retry_on_timeout=10)

if os.path.isfile('.uuid'):
    with open('.uuid', 'r') as fp:
        UUID = fp.read().strip()
else:
    with open('.uuid', 'w') as fp:
        fp.write(UUID)

def get_network():
    network = {'RX': {
        'bytes': psutil.net_io_counters().bytes_recv,
        'packets': psutil.net_io_counters().packets_recv,
    }, 'TX': {
        'bytes': psutil.net_io_counters().bytes_sent,
        'packets': psutil.net_io_counters().packets_sent,
    }}

    if conn.exists("system_monitor:collection:network:tmp:" + UUID):
        net0 = json.loads(conn.get("system_monitor:collection:network:tmp:" + UUID))
        if network['RX']['packets'] > net0['RX']['packets'] and network['RX']['bytes'] > net0['RX']['bytes'] and \
                network['TX']['packets'] > net0['TX']['packets'] and network['TX']['bytes'] > net0['TX']['bytes']:
            conn.zadd("system_monitor:collection:network:RX:" + UUID,
                      {json.dumps(
                          {"time": TIME, "value": '{},{}'.format(network['RX']['packets'] - net0['RX']['packets'],
                                                                 network['RX']['bytes'] - net0['RX']['bytes'])}): TIME})
            conn.zadd("system_monitor:collection:network:TX:" + UUID,
                      {json.dumps(
                          {"time": TIME, "value": '{},{}'.format(network['TX']['packets'] - net0['TX']['packets'],
                                                                 network['TX']['bytes'] - net0['TX']['bytes'])}): TIME})

    conn.set("system_monitor:collection:network:tmp:" + UUID,
             json.dumps(network), TIME_PERIOD)
    return network


def get_process_num():
    # n-2 '''
    p = subprocess.Popen("ps aux | wc -l", shell=True, stdout=subprocess.PIPE)
    return 
(p.stdout.readline().strip())


def get_cpu_info():
    # core modelname mhz'''
    p = subprocess.Popen("cat /proc/cpuinfo | egrep 'Processor|name' | cut -f2 -d: |uniq", shell=True, stdout=subprocess.PIPE)
    return b2s(p.stdout.readline().strip())


def get_cpu_core():
    # core modelname mhz'''
    return str(psutil.cpu_count())


def get_cpu_temp():
    # core modelname mhz'''
    p = subprocess.Popen("cat /sys/devices/virtual/thermal/thermal_zone0/temp", shell=True, stdout=subprocess.PIPE)
    try:
        tmp = b2s(p.stdout.readline().strip())
        conn.zadd("system_monitor:collection:thermal:" + UUID,
                  {json.dumps({"time": TIME, "value": str(int(tmp)*1.0/1000)}): TIME})
        return tmp
    except:
        return 0


def get_mem_info():
    info = {'Mem': {
        'total': format_MB(psutil.virtual_memory().total),
        'used': format_MB(psutil.virtual_memory().used),
        'free': format_MB(psutil.virtual_memory().free),
    }, 'Swap': {
        'total': format_MB(psutil.swap_memory().total),
        'used': format_MB(psutil.swap_memory().used),
        'free': format_MB(psutil.swap_memory().free)
    }}

    conn.zadd("system_monitor:collection:memory:" + UUID,
              {json.dumps({"time": TIME, "value": format_MB(psutil.virtual_memory().used)}): TIME})

    conn.zadd("system_monitor:collection:swap:" + UUID,
              {json.dumps({"time": TIME, "value": format_MB(psutil.swap_memory().used)}): TIME})
    return info


def get_sys_version():
    # System and version'''
    p = subprocess.Popen(". /usr/lib/os-release;echo $PRETTY_NAME", shell=True, stdout=subprocess.PIPE)

    return b2s(p.stdout.readline().strip())


def get_disk_partitions():
    parts = psutil.disk_partitions(True)
    result = []
    for part in parts:
        result.append(part)
        for i in DISK_EXCLUDE:
            if part.mountpoint.find(i) != -1:
                result.remove(part)
                break
    return result


def get_disk_info():
    # disk: total, usage, free, %'''
    disks = {}

    for partition in get_disk_partitions():
        disk = psutil.disk_usage(partition.mountpoint)
        disks[partition.mountpoint] = {
            'total': format_MB(disk.total),
            'used': format_MB(disk.used),
            'free':  format_MB(disk.free),
            'percent': disk.percent
        }

    conn.zadd("system_monitor:collection:disk:" + UUID,
              {json.dumps({"time": TIME, "value": disks}): TIME})
    return disks


def get_ipv4():
    # interface ipv4'''
    return fetch_url("http://v4.ipv6-test.com/api/myip.php")


def get_ipv6():
    # interface ipv6
    return fetch_url("http://v6.ipv6-test.com/api/myip.php")


def get_connections():
    # establish
    p = subprocess.Popen("netstat -na|grep ESTABLISHED|wc -l", shell=True, stdout=subprocess.PIPE)
    return b2s(p.stdout.readline().strip())


def get_uptime():
    # uptime second
    return time.time() - psutil.boot_time()


def get_cpu_load():
    # uptime second
    p = subprocess.Popen("uptime|awk -F'load average:' '{print $2}'", shell=True, stdout=subprocess.PIPE)
    tmp = b2s(p.stdout.readline().strip()).replace(' ', '').split(",")
    load = {
        '1min': tmp[0],
        '5min': tmp[1],
        '15min': tmp[2]
    }
    conn.zadd("system_monitor:collection:cpu:" + UUID,
              {json.dumps({"time": TIME, "value": str(psutil.cpu_percent())}): TIME})
    return load


def get_aggragate_json():
    info = {
        'Connection': get_connections(),
        'Disk': get_disk_info(),
        'Uptime': get_uptime(),
        'Memory': get_mem_info(),
        'Load': get_cpu_load(),
        'Process': get_process_num(),
        'Network': get_network(),
        'Thermal': get_cpu_temp()
    }
    return json.dumps(info)


def b2s(b):
    return str(b, encoding="utf-8")


def report():
    conn.set("system_monitor:stat:" + UUID, get_aggragate_json())


def delete_offline():
    with conn.pipeline(transaction=False) as p:
        try:
            for k, v in conn.hgetall("system_monitor:hashes").items():
                hashes = bytes.decode(k)
                ip = bytes.decode(v)
                if conn.exsits("system_monitor:info:" + hashes) and TIME - float(conn.hmget("system_monitor:info:" + hashes, 'Update Time')[0]) > TIMEOUT:
                    p.hdel("system_monitor:hashes", hashes)
                    p.delete("system_monitor:info:" + hashes)
                    p.zremrangebyscore("system_monitor:collection:cpu:" + hashes, 0, TIME)
                    p.zremrangebyscore("system_monitor:collection:disk:" + hashes, 0, TIME)
                    p.zremrangebyscore("system_monitor:collection:memory:" + hashes, 0, TIME)
                    p.zremrangebyscore("system_monitor:collection:swap:" + hashes, 0, TIME)
                    p.zremrangebyscore("system_monitor:collection:network:RX:" + hashes, 0, TIME)
                    p.zremrangebyscore("system_monitor:collection:network:TX:" + hashes, 0, TIME)
                    p.delete("system_monitor:stat:" + hashes)
                    p.execute()
        except:
            pass


def format_MB(v):
    return '%.2f' % (v * 1.0 / 1048576)


def fetch_url(url):
    i = 5
    while i > 0:
        try:
            resp = requests.get(url=url, timeout=5)
            if resp.status_code == 200:
                return resp.text
        except:
            i = i - 1
    return "None"


def report_once():
    """ip"""
    global IP, TIME
    IP = get_ipv4()

    info = {
        "CPU": get_cpu_core() + "x " + get_cpu_info(),
        "System Version": get_sys_version(),
        "IPV4": re.sub("[0-9]*\\.[0-9]*\\.[0-9]*", "*.*.*", get_ipv4()),
        "IPV6": re.sub("[a-zA-Z0-9]*:", "*:", get_ipv6()),
        "Update Time": TIME
    }
    with conn.pipeline(transaction=False) as pipeline:
        pipeline.hmset("system_monitor:hashes", {UUID: IP})
        pipeline.hmset("system_monitor:info:" + UUID, info)
        pipeline.zremrangebyscore("system_monitor:collection:cpu:" + UUID, 0, TIME - TIME_PERIOD)
        pipeline.zremrangebyscore("system_monitor:collection:thermal:" + UUID, 0, TIME - TIME_PERIOD)
        pipeline.zremrangebyscore("system_monitor:collection:disk:" + UUID, 0, TIME - TIME_PERIOD)
        pipeline.zremrangebyscore("system_monitor:collection:memory:" + UUID, 0, TIME - TIME_PERIOD)
        pipeline.zremrangebyscore("system_monitor:collection:swap:" + UUID, 0, TIME - TIME_PERIOD)
        pipeline.zremrangebyscore("system_monitor:collection:network:RX:" + UUID, 0, TIME - TIME_PERIOD)
        pipeline.zremrangebyscore("system_monitor:collection:network:TX:" + UUID, 0, TIME - TIME_PERIOD)
        pipeline.execute()

    report()
    delete_offline()
    conn.close()


report_once()
