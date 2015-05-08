:: Build 64bit
call "C:\grr\vagrant\windows\64bitenv.bat"
cd sleuthkit-4.1.3
cmd /c "msbuild win32\libtsk\libtsk.vcxproj /p:Configuration=Release;Platform=x64 || echo "tsk 64bit build failed" && exit /b 1"

:: Stick libs somewhere they are loadable
xcopy win32\libtsk\x64\Release\libtsk.lib C:\PYTHON_64\libs\ /e /h /y
:: This is where the pytsk setup.py expects them to be
xcopy win32\libtsk\x64\Release\libtsk.lib win32\x64\Release\ /e /h /y
cd %USERPROFILE%

cd pytsk
cmd /c "python generate_bindings.py ..\sleuthkit-4.1.3"
cmd /c "msbuild msvscpp\pytsk3.sln /p:Configuration=Release;Platform=x64 || echo "pytsk 64bit build failed" && exit /b 1"
cmd /c "python setup.py install && python -c "import pytsk3" || exit /b 1" || echo "pytsk 64bit install failed" && exit /b 1"
cd %USERPROFILE%

