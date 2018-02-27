echo Installing GRR dependencies

mkdir C:\grr_deps || echo "Failed to create C:\grr_deps" && exit /b 1
cd C:\grr_deps

echo Installing 64bit python and pip
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/2.7.13/python-2.7.13.amd64.msi', 'C:\grr_deps\python-2.7.13.amd64.msi')" || echo "64bit python download failed" && exit /b 1

:: These Python paths were chosen to match appveyor since python will silently
:: refuse to install if it is already installed elsewhere:
:: http://www.appveyor.com/docs/installed-software#python
::
:: There's some weirdness with server versions of windows and installing python
:: with pip.  Happens on both azure and GCP, the workaround is to install twice.
:: http://stackoverflow.com/questions/28404878/fail-to-install-python-2-7-9-on-a-windows-google-compute-engine-instance
start /wait msiexec.exe /i "C:\grr_deps\python-2.7.13.amd64.msi" /passive ADDLOCAL="all" REMOVE="pip_feature" TARGETDIR="C:\Python27-x64" ALLUSERS=1 || echo "python no pip failed" && exit /b 1
start /wait msiexec.exe /i "C:\grr_deps\python-2.7.13.amd64.msi" /passive ADDLOCAL="all" TARGETDIR="C:\Python27-x64" ALLUSERS=1 || echo "python with pip failed" && exit /b 1
C:\Python27-x64\python.exe --version || echo "64bit python missing" && exit /b 1
C:\Python27-x64\python.exe -m pip install --upgrade "pip>=8.1.1"
C:\Python27-x64\Scripts\pip.exe install --upgrade virtualenv
C:\Python27-x64\Scripts\virtualenv.exe --version || echo "64bit virtualenv install failed" && exit /b 1

echo Installing 32bit python and pip
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/2.7.13/python-2.7.13.msi', 'C:\grr_deps\python-2.7.13.msi')"
start /wait msiexec.exe /i "C:\grr_deps\python-2.7.13.msi" /passive ADDLOCAL="all" REMOVE="pip_feature" TARGETDIR="C:\Python27" ALLUSERS=1
start /wait msiexec.exe /i "C:\grr_deps\python-2.7.13.msi" /passive ADDLOCAL="all" TARGETDIR="C:\Python27" ALLUSERS=1
C:\Python27\python.exe --version || echo "32bit python install failed" && exit /b 1
C:\Python27\python.exe -m pip install --upgrade "pip>=8.1.1"
C:\Python27\Scripts\pip.exe install --upgrade virtualenv
C:\Python27\Scripts\virtualenv.exe --version || echo "32bit virtualenv install failed" && exit /b 1

:: Get the Microsoft Visual C++ Compiler for Python 2.7
:: http://aka.ms/vcpython27
echo Installing Microsoft Visual C++ Compiler for Python 2.7
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://download.microsoft.com/download/7/9/6/796EF2E4-801B-4FC4-AB28-B59FBF6D907B/VCForPython27.msi', 'C:\grr_deps\VCForPython27.msi')"
start /wait msiexec.exe /i C:\grr_deps\VCForPython27.msi /passive

:: Install protobuf compiler - needed for building sdist
:: GitHub is not happy with older versions of TLS, so we're explicitly specifying TLS v1.2 as the protocol version.
echo Installing protobuf compiler
powershell -NoProfile -ExecutionPolicy unrestricted -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (new-object System.Net.WebClient).DownloadFile('https://github.com/google/protobuf/releases/download/v3.3.0/protoc-3.3.0-win32.zip', 'C:\grr_deps\protoc-3.3.0-win32.zip')"
C:\Python27-x64\python.exe -m "zipfile" -e C:\grr_deps\protoc-3.3.0-win32.zip C:\grr_deps\protoc
C:\grr_deps\protoc\bin\protoc.exe --version || echo "proto compiler install failed" && exit /b 1

:: Install Google Cloud SDK
echo Installing Google Cloud SDK
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-163.0.0-windows-x86_64.zip', 'C:\grr_deps\google-cloud-sdk-163.0.0-windows-x86_64.zip')"
C:\Python27-x64\python.exe -m "zipfile" -e C:\grr_deps\google-cloud-sdk-163.0.0-windows-x86_64.zip C:\grr_deps
C:\grr_deps\google-cloud-sdk\install.bat --quiet || echo "Google Cloud SDK installation failed" && exit /b 1

echo GRR dependency installation complete
