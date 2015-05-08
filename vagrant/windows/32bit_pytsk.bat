:: Build 32bit
call "C:\grr\vagrant\windows\32bitenv.bat"
cd sleuthkit-4.1.3
cmd /c "msbuild win32\libtsk\libtsk.vcxproj /p:Configuration=Release;Platform=Win32 || echo "tsk 32bit build failed" && exit /b 1"

:: Stick libs somewhere they are loadable
xcopy win32\libtsk\Release\libtsk.lib win32\Release\ /e /h /y
:: This is where the pytsk setup.py expects them to be
xcopy win32\libtsk\Release\libtsk.lib C:\PYTHON_32\libs\ /e /h /y
cd %USERPROFILE%

cd pytsk
cmd /c "python generate_bindings.py ..\sleuthkit-4.1.3"
cmd /c "msbuild msvscpp\pytsk3.sln /p:Configuration=Release;Platform=Win32 || echo "pytsk 32bit build failed" && exit /b 1"
cmd /c "python setup.py install && python -c "import pytsk3" || exit /b 1" || echo "pytsk 32bit install failed" && exit /b 1
cd %USERPROFILE%
