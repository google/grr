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

:: Standard Win7 powershell can no longer establish an SSL connection to
:: openssl.org.  Download over http and use fciv to verify.
choco install fciv -y || echo "fciv install failed" && exit /b 1
mkdir %SYSTEMDRIVE%\openssl
cd %SYSTEMDRIVE%\openssl
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('http://www.openssl.org/source/openssl-1.0.2d.tar.gz', '%SYSTEMDRIVE%\openssl\openssl-1.0.2d.tar.gz')" || echo "Couldn't download openssl" && exit /b 1
fciv -sha1 %SYSTEMDRIVE%\openssl\openssl-1.0.2d.tar.gz | findstr /C:"d01d17b44663e8ffa6a33a5a30053779d9593c3d" || echo "Bad hash for openssl" && exit /b 1
7z e openssl-1.0.2d.tar.gz

