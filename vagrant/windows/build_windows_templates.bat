:: Before running this, get dependencies and set up virtualenvs by running
:: install_for_build.bat
:: This script will download a sdist from cloud storage (put it there using
:: scripts/make_sdist_for_templates.sh) and use it to build 32
:: and 64bit templates.

rd /s /q C:\grrbuild
mkdir C:\grrbuild
mkdir C:\grrbuild\output
cd \grrbuild

:: Get the sdist from cloudstorage, this assumes there is only one to avoid
:: hardcoding version numbers.
gsutil cp "gs://grr-releases-testing/grr-response-core-*.tar.gz" .
gsutil cp "gs://grr-releases-testing/grr-response-client-*.tar.gz" .

:: Ghetto hack to avoid hardcoding version number, pip install *.tar.gz doesn't
:: work.
dir /b grr-response-client-*.tar.gz > client.txt
set /p CLIENT_TARBALL=<client.txt
dir /b grr-response-core-*.tar.gz > core.txt
set /p CORE_TARBALL=<core.txt

:: Build 64bit
:: Make sure we have the latest copies of dependencies as specified in setup.py
cmd /c ""C:\PYTHON_64\Scripts\activate" && pip install --upgrade %CORE_TARBALL%" || echo "grr-response-core-64 install failed" && exit /b 1
cmd /c ""C:\PYTHON_64\Scripts\activate" && pip install --upgrade %CLIENT_TARBALL%" || echo "grr-response-client-64 install failed" && exit /b 1

:: We dont need to run special compilers so just enter the virtualenv and build.
:: Python will already find its own MSVC for python compilers.
cmd /c ""C:\PYTHON_64\Scripts\activate" && grr_client_build --arch amd64 --verbose build --output \grrbuild\output" || echo "64bit build failed" && exit /b 1
cmd /c ""C:\PYTHON_64\Scripts\activate" && grr_client_build build_components --output \grrbuild\output" || echo "64bit component build failed" && exit /b 1

:: Build 32bit
cmd /c ""C:\PYTHON_32\Scripts\activate" && pip install --upgrade %CORE_TARBALL%" || echo "grr-response-core-32 install failed" && exit /b 1
cmd /c ""C:\PYTHON_32\Scripts\activate" && pip install --upgrade %CLIENT_TARBALL%" || echo "grr-response-client-32 install failed" && exit /b 1

cmd /c ""C:\PYTHON_32\Scripts\activate" && grr_client_build --arch i386 --verbose build --output \grrbuild\output" || echo "32bit build failed" && exit /b 1
cmd /c ""C:\PYTHON_32\Scripts\activate" && grr_client_build build_components --output \grrbuild\output" || echo "32bit component build failed" && exit /b 1

gsutil -m cp C:\grrbuild\output\* "gs://grr-releases-testing/"

