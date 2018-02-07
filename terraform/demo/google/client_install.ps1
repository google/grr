function Write-SerialPort {
    param (
      [string]$message
    )

    $port = New-Object System.IO.Ports.SerialPort COM1,9600,None,8,one
    $port.open()
    $port.WriteLine($message)
    $port.Close()
}

Write-SerialPort ('Downloading client')

$down = New-Object System.Net.WebClient
$url  = '${windows_installer_download_url}';
$file = 'grr-install.exe';
$down.DownloadFile($url,$file);

Write-SerialPort ('Installing client')

$exec = New-Object -com shell.application
$exec.shellexecute($file);

Write-SerialPort ('Done')
