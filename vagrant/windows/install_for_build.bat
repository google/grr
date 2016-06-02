mkdir C:\grr_deps
cd C:\grr_deps

:: Get 64 bit python and pip
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/2.7.11/python-2.7.11.amd64.msi', 'python-2.7.11.amd64.msi')"
start /wait msiexec.exe /i "python-2.7.11.amd64.msi" /passive TARGETDIR="C:\grr_deps\Python27" ALLUSERS=1
C:\grr_deps\Python27\Scripts\pip.exe install --upgrade pip
C:\grr_deps\Python27\Scripts\pip.exe install --upgrade virtualenv

:: Get 32 bit python and pip
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/2.7.11/python-2.7.11.msi', 'python-2.7.11.msi')"
start /wait msiexec.exe /i "python-2.7.11.msi" /passive TARGETDIR="C:\grr_deps\Python27_32" ALLUSERS=1
C:\grr_deps\Python27_32\Scripts\pip.exe install --upgrade pip
C:\grr_deps\Python27_32\Scripts\pip.exe install --upgrade virtualenv

:: Get the Microsoft Visual C++ Compiler for Python 2.7
:: http://aka.ms/vcpython27
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://download.microsoft.com/download/7/9/6/796EF2E4-801B-4FC4-AB28-B59FBF6D907B/VCForPython27.msi', 'VCForPython27.msi')"
start /wait msiexec.exe /i VCForPython27.msi

:: Install protobuf compiler - needed for building sdist
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://github.com/google/protobuf/releases/download/v2.6.1/protoc-2.6.1-win32.zip', 'protoc-2.6.1-win32.zip')"
C:\grr_deps\Python27\python.exe -m "zipfile" -e protoc-2.6.1-win32.zip protoc
