:: Install the extra things we need to build openssl from src.
choco install nasm -y || echo "nasm install failed" && exit /b 1
SETX /M PATH "%PATH%;C:\Program Files (x86)\nasm"
call refreshenv

choco install 7zip.install -y || echo "7zip install failed" && exit /b 1
SETX /M PATH "%PATH%;%PROGRAMFILES%\7-Zip"
call refreshenv

:: choco install activeperl is broken, strawberry perl doesn't work with openssl
:: http://developer.covenanteyes.com/building-openssl-for-visual-studio/
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://downloads.activestate.com/ActivePerl/releases/5.20.2.2001/ActivePerl-5.20.2.2001-MSWin32-x86-64int-298913.msi', 'ActivePerl-5.20.2.2001-MSWin32-x86-64int-298913.msi')"
msiexec /I ActivePerl-5.20.2.2001-MSWin32-x86-64int-298913.msi /q || echo "perl install failed" && exit /b 1
SETX /M PATH "%PATH%;%SYSTEMDRIVE%\Perl\bin"
call refreshenv

mkdir %SYSTEMDRIVE%\openssl
cd %SYSTEMDRIVE%\openssl
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://www.openssl.org/source/openssl-1.0.2c.tar.gz', '%SYSTEMDRIVE%\openssl\openssl-1.0.2c.tar.gz')" || echo "Couldn't download openssl" && exit /b 1
7z e openssl-1.0.2c.tar.gz

