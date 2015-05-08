::Installing a 32bit virtualenv onto a machine that already has 64bit python is
::tricky. We need to be explicit about where pip and virtualenv need to get
::installed themselves, and prevent the 64bit versions from being used. So we
::temporarily mess with path and pythonhome to achieve this.
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')"
set PYTHONHOME=C:\tools\python2-x86_32
PATH=C:\tools\python2-x86_32 && C:\tools\python2-x86_32\python.exe get-pip.py
C:\tools\python2-x86_32\Scripts\pip.exe install virtualenv
C:\tools\python2-x86_32\Scripts\virtualenv.exe -p C:\tools\python2-x86_32\python.exe C:\PYTHON_32 || echo "32bit virtualenv failed" && exit /b 1
