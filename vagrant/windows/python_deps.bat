:: Install python dependencies
:: protobuf uses a fancy egg format which seems to mess up PyInstaller,
:: resulting in missing the library entirely. I believe the issue is this:
:: https://github.com/pypa/pip/issues/3#issuecomment-1659959
:: Using --egg installs it in a way that PyInstaller understands
pip install --egg protobuf==2.6.1 || echo "protobuf egg install failed" && exit /b 1

:: That isn't even enough, pyinstaller still fails to include it because there
:: is no __init__.py:
:: https://github.com/google/protobuf/issues/713
type nul >> C:\PYTHON_64\Lib\site-packages\google\__init__.py
type nul >> C:\PYTHON_32\Lib\site-packages\google\__init__.py
pip install -r C:\grr\client\windows\requirements.txt  || echo "python requirements install failed" && exit /b 1

:: Pyinstaller 2.1 is broken, as is head @ 20150422: https://github.com/google/grr/issues/41
:: GRR expects pyinstaller source to be at PyInstaller.path, otherwise we'd
:: install this via requirements.txt
mkdir C:\grr_build\
git clone -b develop https://github.com/pyinstaller/pyinstaller.git C:\grr_build\pyinstaller
cd C:\grr_build\pyinstaller
git reset --hard edb5d438d8df5255a5c8f70f42f11f75aa4e08cf
python setup.py install
cd ..

:: Use rekall script to install yara as a static library
git clone https://github.com/google/rekall.git
cd rekall
git submodule update --init --recursive
cd third_party\python-yara\
python setup.py install
cd ..\..\..\

:: Check the most complicated python bits here
python -c "import M2Crypto" || echo "M2Crypto install failed" && exit /b 1
python -c "from rekall import plugins" || echo "rekall install failed" && exit /b 1
python -c "import google.protobuf" || echo "protobuf install failed" && exit /b 1
python -c "import win32api" || echo "pywin32 install failed" && exit /b 1
python -c "import psutil" || echo "psutil install failed" && exit /b 1
python -c "import PyInstaller" || echo "PyInstaller install failed" && exit /b 1
python -c "import yara" || echo "Yara install failed" && exit /b 1


