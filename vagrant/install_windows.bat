:: This script is tested on Win7 x64 SP1 and builds environments for both 32 and
:: 64 bit clients.  We expect SP1, visualstudiocommunity2013, windows 7 SDK,
:: chocolatey and cygwin to already be installed by running
:: install_visual_studio.bat separately, since installing them is very slow and
:: requires multiple reboots.

:: Not strictly neccessary since this should be a new shell, but use this to
:: test if chocolatey got installed.

call refreshenv || echo "refreshenv failed - run install_visual_studio.bat first" && exit /b 1

:: python chocolatey packages are broken since the MSI doesn't accept ALLUSERS,
:: so we do this ourselves. 64bit
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/2.7.9/python-2.7.9.amd64.msi', 'python-2.7.9.amd64.msi')"
msiexec /i "python-2.7.9.amd64.msi" /passive TARGETDIR="C:\tools\python2" || echo "64bit python install failed" && exit /b 1
SETX PATH ""
SETX /M PATH "%PATH%;C:\tools\python2;C:\tools\python2\Scripts"
call refreshenv

powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/2.7.9/python-2.7.9.msi', 'python-2.7.9.msi')"
msiexec /i "python-2.7.9.msi" /passive TARGETDIR="C:\tools\python2-x86_32" || echo "32bit python install failed" && exit /b 1

:: This should put git on the path, but it doesn't
choco install git -y || echo "git install failed" && exit /b 1
SETX /M PATH "%PATH%;C:\Program Files (x86)\Git\bin"
:: Kill the broken version of perl that git ships, we install activestate perl
:: later.  This one doesn't work with openssl.
del /f /s "C:\Program Files (x86)\Git\bin\perl.exe"
call refreshenv

:: Currently 3.0.2, good because 3.0.5 breaks M2Crypto
:: https://github.com/M2Crypto/M2Crypto/issues/24
choco install swig -y || echo "swig install failed" && exit /b 1
SETX /M PATH "%PATH%;%ALLUSERSPROFILE%\chocolatey\lib\swig\tools\swigwin-3.0.2"
call refreshenv

C:\tools\python2\Scripts\pip.exe install virtualenv || echo "virtualenv install failed" && exit /b 1

C:\tools\python2\Scripts\virtualenv -p C:\tools\python2\python.exe C:\PYTHON_64 || echo "64bit virtualenv failed" && exit /b 1

cmd /c "C:\grr\vagrant\windows\32bit_virtualenv.bat" || echo "32bit virtualenv failed" && exit /b 1

cmd /c "C:\grr\vagrant\windows\openssl_deps.bat" || echo "openssl_deps.bat failed" && exit /b 1
call refreshenv

cmd /c "C:\grr\vagrant\windows\32bitopenssl.bat" || echo "32bitopenssl.bat failed" && exit /b 1
cmd /c "C:\grr\vagrant\windows\64bitopenssl.bat" || echo "64bitopenssl.bat failed" && exit /b 1

cmd /c "C:\grr\vagrant\windows\install_pytsk.bat" || echo "install_pytsk.bat failed" && exit /b 1
call refreshenv

cmd /c ""C:\grr\vagrant\windows\64bitenv.bat" && C:\grr\vagrant\windows\python_deps.bat" || echo "64bitpython_deps.bat failed" && exit /b 1
cmd /c ""C:\grr\vagrant\windows\32bitenv.bat" && C:\grr\vagrant\windows\python_deps.bat" || echo "32bitpython_deps.bat failed" && exit /b 1
