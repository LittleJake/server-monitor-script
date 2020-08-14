import redis, subprocess, time, json, hashlib, re, math

HOST = ""
PORT = ""
PASSWORD = ""
SALT = ""
IP = "0.0.0.0"
conn = redis.Redis(host=HOST, password=PASSWORD, port=PORT, retry_on_timeout=10)
TIME = math.floor(time.time())


def get_process_num():
    # n-2 '''
    p = subprocess.Popen("ps aux | wc -l",shell=True,stdout=subprocess.PIPE)
    return p.stdout.readline().strip()


def get_cpu_info():
    # core modelname mhz'''
    p = subprocess.Popen("cat /proc/cpuinfo | grep name | cut -f2 -d: |uniq",shell=True,stdout=subprocess.PIPE)
    return p.stdout.readline().strip()


def get_cpu_core():
    # core modelname mhz'''
    p = subprocess.Popen("cat /proc/cpuinfo |grep cores|wc -l",shell=True,stdout=subprocess.PIPE)
    return p.stdout.readline().strip()


def get_cpu_frequency():
    # core modelname mhz'''
    p = subprocess.Popen("cat /proc/cpuinfo |grep MHz|cut -f2 -d: |uniq",shell=True,stdout=subprocess.PIPE)
    return p.stdout.readline().strip()


def get_mem_info():
    global IP, TIME
    # Mem/Swap'''
    p = subprocess.Popen("free -m|grep -E '(Mem|Swap)'|awk -F' ' '{print $2,$3,$4}'",shell=True,stdout=subprocess.PIPE)
    info = {}
    # Mem
    tmp = p.stdout.readline().strip().split()
    info['Mem'] = {
        'total': tmp[0],
        'used': tmp[1],
        'free': tmp[2]
    }
    
    conn.zadd("system_monitor:collection:memory:"+IP,{json.dumps({"time": TIME, "value": str(tmp[1])}):TIME})
    # Swap
    tmp = p.stdout.readline().strip().split()
    info['Swap'] = {
        'total': tmp[0],
        'used': tmp[1],
        'free': tmp[2]
    }
    conn.zadd("system_monitor:collection:swap:"+IP,{json.dumps({"time": TIME, "value": str(tmp[1])}):TIME})
    return info


def get_sys_version():
    # System and version'''
    p = subprocess.Popen("cat /etc/redhat-release",shell=True,stdout=subprocess.PIPE)

    return p.stdout.readline().strip()


def get_disk_info():
    global IP, TIME
    # disk: total, usage, free, %'''
    p = subprocess.Popen("df -h --total /|grep total|awk -F' ' '{print $2,$3,$4,$5}'",shell=True,stdout=subprocess.PIPE)
    tmp = p.stdout.readline().strip().split()
    info = {
        'total': tmp[0],
        'used': tmp[1],
        'free': tmp[2],
        'percent': tmp[3]
    }
    conn.zadd("system_monitor:collection:disk:"+IP,{json.dumps({"time": TIME, "value": str(tmp[1])}):TIME})
    return info


def get_ipv4():
    # interface ipv4'''
    p = subprocess.Popen("ip addr show scope global|grep inet\ |awk -F' ' '{print $2}'",shell=True,stdout=subprocess.PIPE)
    return stdout_trim(p.stdout.readlines())


def get_ipv6():
    # interface ipv6
    p = subprocess.Popen("ip addr show scope global|grep inet6|awk -F' ' '{print $2}'",shell=True,stdout=subprocess.PIPE)
    return stdout_trim(p.stdout.readlines())


def get_connections():
    # establish
    p = subprocess.Popen("netstat -na|grep ESTABLISHED|wc -l",shell=True,stdout=subprocess.PIPE)
    return p.stdout.readline().strip()


def get_uptime():
    # uptime second
    p = subprocess.Popen("cat /proc/uptime|awk -F' ' '{print $1}'",shell=True,stdout=subprocess.PIPE)
    return p.stdout.readline().strip()

def get_cpu_load():
    global IP, TIME
    # uptime second
    p = subprocess.Popen("uptime|awk -F'load average:' '{print $2}'",shell=True,stdout=subprocess.PIPE)
    tmp = p.stdout.readline().strip().replace(' ','').split(",")
    load = {
        '1min': tmp[0],
        '5min': tmp[1],
        '15min': tmp[2]
    }
    conn.zadd("system_monitor:collection:cpu:"+IP,{json.dumps({"time": TIME, "value": str(tmp[1])}):TIME})
    return load

def stdout_trim(so):
    for i in range(0, len(so)):
        so[i] = so[i].strip()
    return so
    
def get_aggragate_json():
    info = {
        'Connection': get_connections(),
        'Disk': get_disk_info(),
        'Uptime': get_uptime(),
        'Memory': get_mem_info(),
        'Load': get_cpu_load(),
        'Process': get_process_num()
    }
    return json.dumps(info)


def report():
    conn.set("system_monitor:stat:"+IP, get_aggragate_json())
    

def report_once():
    '''ip'''
    global IP, TIME
    ip = get_ipv4()
    if len(ip) > 0:
        IP = ip[0]
        
    info = {
        "CPU":get_cpu_core()+"x "+get_cpu_info()+" @"+get_cpu_frequency()+"MHz",
        "System Version": get_sys_version(),
        "IPV4": re.sub("\.[0-9]*",".*", ",".join(get_ipv4())),
        "IPV6": re.sub(":[a-zA-Z0-9]*",":*", ",".join(get_ipv6())),
        "Update Time": TIME
    }
    
    conn.sadd("system_monitor:nodes",IP)
    conn.hmset("system_monitor:hashes",{hashlib.sha256(IP+SALT).hexdigest(): IP})
    conn.hmset("system_monitor:info:"+IP,info)
    conn.zremrangebyscore("system_monitor:collection:cpu:"+IP,0,TIME-86400)
    conn.zremrangebyscore("system_monitor:collection:disk:"+IP,0,TIME-86400)
    conn.zremrangebyscore("system_monitor:collection:memory:"+IP,0,TIME-86400)
    conn.zremrangebyscore("system_monitor:collection:swap:"+IP,0,TIME-86400)
    report()


report_once()
