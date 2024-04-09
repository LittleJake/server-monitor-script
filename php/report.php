<?php


Class Report {
    const IPV4_API = "http://v4.ipv6-test.com/api/myip.php";
    const IPV6_API = "http://v6.ipv6-test.com/api/myip.php";
    private $system = "";
    private $info = [];

    private $stat = [];



    public function __construct(){
        // $this-> stat = [
        //     'Disk' => self::getDiskInfo(),
        //     'Memory' => self::getMemInfo(),
        //     'Load' => self::getLoad(),
        //     'Network' => self::getNetwork(),
        //     'Thermal' => self::getTemp(),
        //     'Battery' => self::getBattery(),
        // ];

        // $this -> info = [
        //     "CPU" => sprintf("%sx %s", self::getCpuCore(), self::getCpuName() ),
        //     "System Version" => self::getSysVersion(),
        //     "IPV4" => re.sub("[0-9]*\.[0-9]*\.[0-9]*", "*.*.*", self::getIPv4()),
        //     "IPV6" => re.sub("[a-zA-Z0-9]*:", "*:", self::getIPv6()),
        //     'Uptime' => self::getUptime(),
        //     'Connection' => self::getConnections(),
        //     'Process' => self::getProcessNum(),
        //     'Load Average' => self::getLoadAverage(),
        //     "Update Time" => time(),
        //     "Country" => COUNTRY[0],
        //     "Country Code" => "CN" if COUNTRY[1] in ("TW", "HK", "MO") else COUNTRY[1],
        //     "Throughput" => sprintf("↓%.2f GB / ↑%.2f GB", NET_FORMER.bytes_recv/1073741824, NET_FORMER.bytes_sent/1073741824),
        // ];
        
    }

    public static function getIPv4() {
        return self::curlGet(self::IPV4_API);
    } 
    public static function getIPv6() {
        return self::curlGet(self::IPV6_API);
    } 

    public static function getSysVersion() {
        if ($fp = @file_get_contents('/etc/os-release')) {
            preg_match('/PRETTY_NAME="(.*)"/', $fp, $os);
            return $os[1];
        }

        return php_uname('s');
    } 
    public static function getLoadAverage() {
        return function_exists("sys_getloadavg")?join(", ", sys_getloadavg()):"Not support.";
    } 
    public static function getUptime() {
        if (strpos(strtolower(php_uname('s')), 'windows') != -1)
            require_once("WindowsUptime.class.php");

        $windowsUptime = new WindowsUptime();

        return $windowsUptime->uptime();
    } 

    private static function curlGet($url = "") {
        // 检查CURL扩展是否安装
        if (in_array('curl', get_loaded_extensions())) {
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
            curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
            $response = curl_exec($ch);
            curl_close($ch);
            return $response;

        } else {
            $opts = [
                'http'=> [
                    'method' => "GET",
                    'timeout' => 5,
                ]
            ];
            $context = stream_context_create($opts);
            $resp = file_get_contents($url, false, $context);
            if (!empty($resp)) {
                return $resp;
            }
            return null;
        }
    } 

    public function report() {
        
    }

    public static function debug(){
        print_r(Report::getIPv4()."\n");
        print_r(Report::getIPv6()."\n");
        print_r(Report::getSysVersion()."\n");
        print_r(Report::getUptime()."\n");
        print_r(Report::getLoadAverage()."\n");

    }
}

$report = new Report();

Report::debug();