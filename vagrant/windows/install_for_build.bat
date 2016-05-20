:: Get python and pip
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/2.7.11/python-2.7.11.amd64.msi', 'python-2.7.11.amd64.msi')"
start /wait msiexec.exe /i python-2.7.11.amd64.msi
C:\Python27\Scripts\pip.exe install --upgrade pip
C:\Python27\Scripts\pip.exe install --upgrade virtualenv
C:\Python27\Scripts\virtualenv.exe C:\PYTHON_64

cmd /c ""C:\PYTHON_64\Scripts\activate" && pip install virtualenv" || echo "virtualenv 64 install failed" && exit /b 1

:: Choose C:\Python27_32 install directory for 32bit
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/2.7.11/python-2.7.11.msi', 'python-2.7.11.msi')"
start /wait msiexec.exe /i python-2.7.11.msi
C:\Python27_32\Scripts\pip.exe install --upgrade pip
C:\Python27_32\Scripts\pip.exe install --upgrade virtualenv
C:\Python27_32\Scripts\virtualenv.exe C:\PYTHON_32

cmd /c ""C:\PYTHON_32\Scripts\activate" && pip install virtualenv" || echo "virtualenv 32 install failed" && exit /b 1

:: Get the Microsoft Visual C++ Compiler for Python 2.7
:: http://aka.ms/vcpython27
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://download.microsoft.com/download/7/9/6/796EF2E4-801B-4FC4-AB28-B59FBF6D907B/VCForPython27.msi', 'VCForPython27.msi')"
start /wait msiexec.exe /i VCForPython27.msi

