<?php

/**
 * Windows Uptime Class
 *
 * http://pmav.eu/stuff/php-windows-uptime/
 *
 * v1.0 - 17/Oct/2008
 * v1.1 - 10/Sep/2009
 */

class WindowsUptime {

  const DEFAULT_FILE = ['c:\pagefile.sys', 'c:\swapfile.sys', 'c:\hiberfil.sys'];
  const DEFAULT_DATE_FORMAT = 'd/M/Y @ H:i';
  const RAW_OUTPUT = true;
  private $file;


  function __construct($file = self::DEFAULT_FILE) {
    $this->file = $file;
  }

  public function uptime($rawOutput = false) {
    $uptime = time();
    foreach($this->file as $f) {
      $modtime = @filemtime($f);
      if (empty($modtime)){
        continue;
      } else {
        $uptime = (time() - $modtime);
        break;
      }
    }
    
    if (empty($modtime)) return "Not support.";

    if (!$rawOutput) {
      $days = floor($uptime / (24 * 3600));
      $uptime = $uptime - ($days * (24 * 3600));
      $hours = floor($uptime / (3600));
      $uptime = $uptime - ($hours * (3600));
      $minutes = floor($uptime / (60));
      $uptime = $uptime - ($minutes * 60);
      $seconds = $uptime;

      $days = $days.' day'.($days != 1 ? 's' : '');
      $hours = $hours.' hour'.($hours != 1 ? 's' : '');
      $minutes = $minutes.' minute'.($minutes != 1 ? 's' : '');
      $seconds = $seconds.' second'.($seconds != 1 ? 's' : '');

      $uptime = $days.' '.$hours.' '.$minutes.' '.$seconds;
    }

    return $uptime;
  }

  public function getFile() {
    return $this->file;
  }

  public function setFile($file) {
    $this->file = $file;
  }

}

