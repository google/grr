:: Install chocolatey
powershell -NoProfile -ExecutionPolicy unrestricted -Command "iex ((new-object net.webclient).DownloadString('https://chocolatey.org/install.ps1'))" && SET PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin || echo "chocolatey install failed" && exit /b 1

:: Chocolately refuses to run despite being on PATH until you open a new cmd
:: shell. We hardcode the path here to make it work until the user starts a new shell
:: in the next step.
:: Note VS2013 requires Win7 SP1
cmd /c "%ALLUSERSPROFILE%\chocolatey\bin\choco.exe install visualstudiocommunity2013 -y" || echo "VS2013 install failed" && exit /b 1

:: VS2013 community edition requires the SDK to build 64bit.
cmd /c "%ALLUSERSPROFILE%\chocolatey\bin\choco.exe install windows-sdk-7.1 -y" || echo "Win 7 SDK install failed" && exit /b 1

:: GRR build process expects cygwin 'make.exe'.
:: https://cygwin.com/faq/faq.html#faq.setup.cli
cmd /c "%ALLUSERSPROFILE%\chocolatey\bin\choco.exe install cygwin -y -overrideArgs -installArgs "-q -R C:\tools\cygwin -P make -l C:\tools\cygwin\packages -s http://mirrors.sonic.net/cygwin/"" || echo "cygwin install failed" && exit /b 1
