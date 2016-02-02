mkdir %USERPROFILE%\build\
cd %USERPROFILE%\build\ || echo "Cant switch to build directory" && exit /b 1

::Install 32 bit openssl.  Expects tar file in cwd. We delete the openssl dir to
::avoid any 32-64 contamination.
rd /q /s openssl-1.0.2f
7z x -y openssl-1.0.2f.tar

cd openssl-1.0.2f
perl Configure VC-WIN32 --prefix=%USERPROFILE%\build\Build-OpenSSL-VC-32
call ms\do_nasm.bat
nmake -f ms\ntdll.mak
nmake -f ms\ntdll.mak install

:: Set environment variables to let M2Crypto know where OpenSSL lives.
set INCLUDE=%INCLUDE%;%USERPROFILE%\build\Build-OpenSSL-VC-32\include
set LIB=%LIB%;%USERPROFILE%\build\Build-OpenSSL-VC-32\lib
set SWIG_FEATURES=-I%USERPROFILE%\build\Build-OpenSSL-VC-32\include

:: M2Crypto development moved to https://gitlab.com/m2crypto/m2crypto but they
:: have since dropped windows and OSX support:
:: https://gitlab.com/m2crypto/m2crypto/issues/57
:: (fix windows incompatibility with ``select()``) Last comment on this thread
:: explains that windows support is not a priority. Until then we use an older
:: forked version. Hopefully we can deprecate M2Crypto soon!
pip install -I -e git+https://github.com/scudette/M2Crypto.git@master#egg=M2Crypto
python -c "import M2Crypto" || echo "32bit M2Crypto install failed" && exit /b 1
