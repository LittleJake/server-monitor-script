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
from dotenv import load_dotenv
import concurrent.futures
import ping3

# Not a nice package.
try:
    import ipapi
except ImportError:
    pass

VERSION = "Alpha-202506019.1-python3"

# get .env location for pyinstaller
extDataDir = os.getcwd()
if getattr(sys, 'frozen', False):
    extDataDir = sys._MEIPASS
load_dotenv(dotenv_path=os.path.join(extDataDir, '.env'))

# get .env
HOST = os.getenv("HOST", "127.0.0.1")
PORT = os.getenv("PORT", "6379")
PASSWORD = os.getenv("PASSWORD", "")
SSL = os.getenv("SSL", 'False').lower() in ('true', '1', 't')
REPORT_ONCE = os.getenv("REPORT_ONCE", 'False').lower() in ('true', '1', 't')
IPV4_API = os.getenv('IPV4_API', "https://4.ident.me/")
IPV6_API = os.getenv('IPV6_API', "https://6.ident.me/")
REPORT_TIME = int(os.getenv('REPORT_TIME', '60'))
DATA_TIMEOUT = int(os.getenv('DATA_TIMEOUT', '259200'))
RETENTION_TIME = int(os.getenv('RETENTION_TIME', '86400'))
DISK_EXCLUDE = os.getenv('DISK_EXCLUDE','/run,/sys,/boot,/dev,/proc,/var/lib').split(",")
DISK_FS_EXCLUDE = os.getenv('DISK_FS_EXCLUDE', 'tmpfs,overlay').split(",")
DISK_OPTS_EXCLUDE = os.getenv('DISK_OPTS_EXCLUDE', 'ro').split(",")
PROCFS_PATH = os.getenv('PROCFS_PATH', '/proc')
SERVER_URL = os.getenv('SERVER_URL', "")
REPORT_MODE = os.getenv('REPORT_MODE', "redis").lower()
SERVER_TOKEN = os.getenv('SERVER_TOKEN', "")
SOCKET_TIMEOUT = int(os.getenv('SOCKET_TIMEOUT', "10"))
PING_CONCURRENT = int(os.getenv('PING_CONCURRENT', "10"))


# Logging configuration
DEBUG_LEVEL = os.getenv('DEBUG_LEVEL', "20")  # Assuming default level is INFO
logging.basicConfig(level=int(DEBUG_LEVEL), format="%(asctime)s - %(message)s")


# Loading UUID
UUID = str(uuid.uuid4()).replace("-", "")
if os.path.isfile('.uuid'):
    with open('.uuid', 'r') as fp:
        UUID = fp.read().strip()
else:
    with open('.uuid', 'w') as fp:
        fp.write(UUID)

logging.info("Your UUID is: %s" % UUID)

# setting http api upload
SERVER_URL_INFO = "%s/api/report/info/%s" % (SERVER_URL, UUID)
SERVER_URL_COLLECTION = "%s/api/report/collection/%s" % (SERVER_URL, UUID)
SERVER_URL_HASH = "%s/api/report/hash/%s" % (SERVER_URL, UUID)
SERVER_URL_COMMAND = "%s/api/report/command/%s" % (SERVER_URL, UUID)

IPV4 = None
IPV6 = None
COUNTRY = None
TIME = math.floor(time.time())
psutil.PROCFS_PATH = PROCFS_PATH

if REPORT_MODE == "redis":
    conn = redis.Redis(host=HOST, password=PASSWORD, port=PORT, ssl=SSL, retry_on_timeout=SOCKET_TIMEOUT)

PING_IP = {}
# get ip.json
try:
    with open("ip.json", "r") as fp:
        PING_IP = json.load(fp)
except Exception as e:
    logging.info("Error occur when loading ip.json, skipping")


def net_io_counters():
    try:
        return psutil.net_io_counters()._asdict()
    except Exception as e:
        logging.error(e)
        return None
    

def disk_io_counters():
    try:
        return psutil.disk_io_counters()._asdict()
    except Exception as e:
        logging.error(e)
        return None


def get_network():
    global NET_FORMER
    if NET_FORMER is None: return {}

    net_temp = net_io_counters()

    network = {'RX': {
        'bytes': (net_temp.get("bytes_recv") - NET_FORMER.get("bytes_recv")) if (net_temp.get("bytes_recv") - NET_FORMER.get("bytes_recv")) > 0 else 0,
        'packets': (net_temp.get("packets_recv") - NET_FORMER.get("packets_recv")) if (net_temp.get("packets_recv") - NET_FORMER.get("packets_recv")) > 0 else 0,
    }, 'TX': {
        'bytes': (net_temp.get("bytes_sent") - NET_FORMER.get("bytes_sent")) if (net_temp.get("bytes_sent") - NET_FORMER.get("bytes_sent")) > 0 else 0,
        'packets': (net_temp.get("packets_sent") - NET_FORMER.get("packets_sent")) if (net_temp.get("packets_sent") - NET_FORMER.get("packets_sent")) > 0 else 0,
    }}

    NET_FORMER = net_temp
    return network


def get_io():
    global IO_FORMER
    if IO_FORMER is None: return {}

    io_temp = disk_io_counters()

    io = {'read': {
        'count': (io_temp.get("read_count") - IO_FORMER.get("read_count")) if (io_temp.get("read_count") - IO_FORMER.get("read_count")) > 0 else 0,
        'bytes': (io_temp.get("read_bytes") - IO_FORMER.get("read_bytes")) if (io_temp.get("read_bytes") - IO_FORMER.get("read_bytes")) > 0 else 0,
        'time': (io_temp.get("read_time") - IO_FORMER.get("read_time")) if (io_temp.get("read_time") - IO_FORMER.get("read_time")) > 0 else 0,
    }, 'write': {
        'count': (io_temp.get("write_count") - IO_FORMER.get("write_count")) if (io_temp.get("write_count") - IO_FORMER.get("write_count")) > 0 else 0,
        'bytes': (io_temp.get("write_bytes") - IO_FORMER.get("write_bytes")) if (io_temp.get("write_bytes") - IO_FORMER.get("write_bytes")) > 0 else 0,
        'time': (io_temp.get("write_time") - IO_FORMER.get("write_time")) if (io_temp.get("write_time") - IO_FORMER.get("write_time")) > 0 else 0,
    }}

    IO_FORMER = io_temp
    return io

def get_process_num():
    return len(psutil.pids())


def get_cpu_name():
    return CPU_INFO.get('brand_raw', CPU_INFO.get('arch_string_raw', 'Unknown'))

def get_load_average():
    try:
        avg = psutil.getloadavg()
    except: return "Not support"
    return "%.2f, %.2f, %.2f" % avg

def get_cpu_core():
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

def get_fan():
    result = {}
    try:
        for sensor_type, sensors in psutil.sensors_fans().items():
            for sensor in sensors:
                result[sensor_type+":"+sensor.label] = sensor.current
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
    # not to display some partitions
    parts = psutil.disk_partitions(False)
    result = []
    for part in parts:
        try:
            result.append(part)
            for i in DISK_EXCLUDE:
                if part.mountpoint.find(i) != -1 or part.fstype in DISK_FS_EXCLUDE or len(set(part.opts.split(",")) & set(DISK_OPTS_EXCLUDE)) > 0:
                    result.remove(part)
                    break
        except: result.remove(part)
                
    return result


def get_disk_info():
    disks = {}

    for partition in get_disk_partitions():
        try:
            disk = psutil.disk_usage(partition.mountpoint)
            disks[partition.mountpoint] = {
                'total': '%.2f' % (disk.total*1.0/1048576),
                'used': '%.2f' % (disk.used*1.0/1048576),
                'free':  '%.2f' % (disk.free*1.0/1048576),
                'percent': disk.percent
            }
        except Exception as e: logging.error(e)

    return disks


def get_request(url=''):
    i = 5
    while i > 0:
        try:
            resp = requests.get(url=url, timeout=SOCKET_TIMEOUT)
            if resp.status_code == 200:
                return resp
        except:
            i = i - 1

    return None


def ping(name, ip):
    try:
        response = ping3.ping(ip, unit="ms")
        if response is None:
            return {name: "0"}
        else:
            return {name: "%.2f" % response}
    except Exception as e:
        logging.debug(e)
        return {name: "0"}



def get_ipv4():
    # interface ipv4
    global IPV4
    if IPV4 is None:
        try:
            resp = get_request(IPV4_API)
            if resp is not None and re.match("\d*\\.\d*\\.\d*",resp.text) is not None:
                IPV4 = resp.text
            else:
                IPV4 = "None"
        except: IPV4 = "None"
    return IPV4


def get_ipv6():
    # interface ipv6
    global IPV6
    if IPV6 is None:
        try:
            resp = get_request(IPV6_API)
            if resp is not None and re.match("[a-fA-F0-9]*:",resp.text) is not None:
                IPV6 = resp.text
            else:
                IPV6 = "None"
        except: IPV6 = "None"
    
    return IPV6

def get_country_ipapi1():
    global COUNTRY,SOCKET_TIMEOUT
    
    if COUNTRY is None:
        try:
            j = ipapi.location(options={"timeout": SOCKET_TIMEOUT})
        except Exception as e: 
            logging.error(e)
            try:
                j = get_request("https://ip-api.io/json").json()
            except Exception as e:
                logging.error(e)
                return None
        
        if j is not None:
            if j["country_name"] in ("Hong Kong", "Macao"):
                j["country_name"] = j["country_name"] + ", SAR"
            elif j["country_name"] == "Taiwan":
                j["country_name"] = j["country_name"] + " Province"
                j["country_code"] = "CN"

            COUNTRY = (j["country_name"], j["country_code"])


def get_country_ipapi2():
    global COUNTRY,SOCKET_TIMEOUT
    
    if COUNTRY is None:
        try:
            j = get_request("http://ip-api.com/json/?fields=country,countryCode").json()
        except Exception as e: 
            logging.error(e)
            return None
        
        if j is not None:
            if j["country"] in ("Hong Kong", "Macao"):
                j["country"] = j["country"] + ", SAR"
            elif j["country"] == "Taiwan":
                j["country"] = j["country"] + " Province"
                j["countryCode"] = "CN"

            COUNTRY = (j["country"], j["countryCode"])


def get_country():
    global COUNTRY
    get_country_ipapi1()
    get_country_ipapi2()

    return ("Unknown", "Unknown") if COUNTRY is None else COUNTRY


def get_connections():
    return "TCP: %d, UDP: %d" % (len(psutil.net_connections("tcp")), len(psutil.net_connections("udp")))

def get_throughput():
    rx = NET_FORMER.get("bytes_recv")/1073741824
    tx = NET_FORMER.get("bytes_sent")/1073741824

    return "{} / {}".format("↓%.2f TB" % (rx/1024) if rx > 1024 else "↓%.2f GB" % rx,
                         "↑%.2f TB" % (tx/1024) if tx > 1024 else "↑%.2f GB" % tx)

def get_uptime():
    t = int(time.time() - psutil.boot_time())
    delta = timedelta(seconds=t)
    return "%d Days %02d:%02d:%02d" % (delta.days, (delta.seconds//3600)%24, (delta.seconds//60)%60, delta.seconds%60)


def get_load():
    return dict(psutil.cpu_times_percent()._asdict())

# TODO: Implement TCPing
# def do_tcping(url, v6=False):
#     get_request(url)

def get_ping():
    ping_result = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=PING_CONCURRENT) as executor:
        futures = [executor.submit(ping, name, ip) for name, ip in PING_IP.items()]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            ping_result.update(result)
            logging.debug(result)

    return ping_result

def get_aggregate_stat_json():
    return json.dumps(get_aggregate_stat())


def get_aggregate_stat():
    info = {
        'Battery': get_battery(),
        'Disk': get_disk_info(),
        'Fan': get_fan(),
        'IO': get_io(),
        'Load': get_load(),
        'Memory': get_mem_info(),
        'Network': get_network(),
        'Ping': get_ping(),
        'Thermal': get_temp(),
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
    logging.debug("{}x {}".format(get_cpu_core(), get_cpu_name()))
    logging.debug(get_sys_version())
    logging.debug(re.sub("\d*\\.\d*\\.\d*", "*.*.*", get_ipv4()))
    logging.debug(re.sub("[a-fA-F0-9]*:", "*:", get_ipv6()))
    logging.debug(get_uptime())
    logging.debug(get_connections())
    logging.debug(get_process_num())
    logging.debug(get_load_average())
    logging.debug(TIME)
    logging.debug(COUNTRY[0])
    logging.debug(COUNTRY[1])
    logging.debug(get_throughput())

    info = {
        'Connection': get_connections(),
        "Country": COUNTRY[0],
        "Country Code": COUNTRY[1],
        "CPU": "{}x {}".format(get_cpu_core(), get_cpu_name()),
        "IPV4": re.sub("\d*\\.\d*\\.\d*", "*.*.*", get_ipv4()),
        "IPV6": re.sub("[a-fA-F0-9]*:", "*:", get_ipv6()),
        'Load Average': get_load_average(),
        'Process': get_process_num(),
        "System Version": get_sys_version(),
        "Throughput": get_throughput(),
        "Update Time": TIME,
        'Uptime': get_uptime(),
        "Agent Version": VERSION
    }
    
    if REPORT_MODE == 'redis':
        with conn.pipeline(transaction=False) as pipeline:
            pipeline.hset(name="system_monitor:hashes", mapping={UUID: IP})
            pipeline.hset(name="system_monitor:info:" + UUID, mapping=info)
            pipeline.zadd("system_monitor:collection:" + UUID, {get_aggregate_stat_json(): TIME})
            
            pipeline.zremrangebyscore("system_monitor:collection:" + UUID, 0, TIME - RETENTION_TIME)
            pipeline.expire("system_monitor:hashes", DATA_TIMEOUT)
            pipeline.expire("system_monitor:info:" + UUID, DATA_TIMEOUT)
            pipeline.expire("system_monitor:collection:" + UUID, DATA_TIMEOUT)
            pipeline.execute()

    elif REPORT_MODE == 'http':
        try:
            if SERVER_TOKEN == "":
                logging.error("Please generate server token using `php think token add --uuid %s` on your central server." % UUID)
                exit(1)
            req = requests.post(url=SERVER_URL_HASH, json={'ip': IPV4}, headers={'authorization': SERVER_TOKEN}, timeout=SOCKET_TIMEOUT)
            if req.status_code != 200: raise Exception(req)
            req = requests.post(url=SERVER_URL_INFO, json=info, headers={'authorization': SERVER_TOKEN}, timeout=SOCKET_TIMEOUT)
            if req.status_code != 200: raise Exception(req)
            req = requests.post(url=SERVER_URL_COLLECTION, json=get_aggregate_stat(), headers={'authorization': SERVER_TOKEN}, timeout=SOCKET_TIMEOUT)
            if req.status_code != 200: raise Exception(req)
        except Exception as e:
            raise Exception("[HTTP%d]: %s, %s" % (e.args[0].status_code, e.args[0].text, e.args[0].url))

    logging.info("Finish Reporting!")

def save_state():
    global NET_FORMER, IO_FORMER, COUNTRY
    with open("dump", "w") as fp:
        fp.write(json.dumps({'NET_FORMER': NET_FORMER,'IO_FORMER': IO_FORMER, 'COUNTRY': COUNTRY}))
       

def get_state():
    global NET_FORMER, IO_FORMER, COUNTRY
    try:
        with open("dump", "r") as fp:
            data = json.loads(fp.read())
            NET_FORMER = data['NET_FORMER']
            IO_FORMER = data['IO_FORMER']
            COUNTRY = data['COUNTRY']
    except:
        logging.info("Former data missing or invalid.")


def get_command():
    if REPORT_MODE == 'redis':
        command = conn.rpop("system_monitor:command:" + UUID)
        return command.decode("utf-8") if command is str else None
    elif REPORT_MODE == 'http':
        try:
            data = requests.get(url=SERVER_URL_COMMAND, headers={'authorization': SERVER_TOKEN}, timeout=SOCKET_TIMEOUT).json()
            return data.get("command")
        except Exception as e:
            logging.error(e)
            return None


def reboot_system():
    try:
        current_os = platform.system()
        if current_os == "Windows":
            os.system("shutdown /r /t 0")
        elif current_os == "Linux":
                os.system("sudo reboot")
    except:
            raise Exception("Reboot command failed.")
    
    NotImplementedError("Reboot command not implemented for this OS")
    

def execute_command():
    command = get_command()
    if command is not None:
        if type(command) == bytes:
            command = command.decode("utf-8")

        if command == "":
            return

        logging.info("Executing command: %s" % command)

        if command == "reboot":
            logging.info("Rebooting...")
            reboot_system()
        elif command == "ping":
            logging.info("Pong!!")
        else:
            logging.info("Command not recognized.")


NET_FORMER = net_io_counters()
IO_FORMER = disk_io_counters()
CPU_INFO = cpuinfo.get_cpu_info()

# Main
def main():
    global REPORT_ONCE, REPORT_TIME

    while not REPORT_ONCE:
        try:
            report_once()
            execute_command()
        except Exception as e:
            logging.error(e)
            logging.error("ERROR OCCUR.")
        time.sleep(REPORT_TIME)

    try:
        get_state()
        report_once()
        execute_command()
        save_state()
        exit(0)
    except Exception as e:
        logging.error(e)
        logging.error("ERROR OCCUR.")
        exit(1)

if __name__ == "__main__":
    main()
