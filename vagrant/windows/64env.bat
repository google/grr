SET PATH=%PATH%;C:\PYTHON_64\libs
"%PROGRAMFILES% (x86)\Microsoft Visual Studio 12.0\VC\bin\amd64\vcvars64.bat"
C:\PYTHON_64\Scripts\activate || echo "virtualenv activate failed" && exit /b 1
SET VS90COMNTOOLS=%VS120COMNTOOLS%
