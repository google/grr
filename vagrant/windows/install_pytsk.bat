:: Install tsk
rd /s /q sleuthkit-4.1.3
del /f /q /s sleuthkit*
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://sourceforge.net/projects/sleuthkit/files/sleuthkit/4.1.3/sleuthkit-4.1.3.tar.gz/download', 'sleuthkit-4.1.3.tar.gz')"
7z e sleuthkit-4.1.3.tar.gz && 7z x sleuthkit-4.1.3.tar
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://googledrive.com/host/0B3fBvzttpiiScUxsUm54cG02RDA/tsk4.1.3_external_type.patch', 'tsk4.1.3_external_type.patch')"
:: Fix segfault https://github.com/py4n6/pytsk/wiki/Building-SleuthKit
git apply -p0 tsk4.1.3_external_type.patch
cd sleuthkit-4.1.3

:: Fix project build file: we don't want libewf and don't have zlib, and we
:: want to target the Windows 7.1 SDK. Upgrade the PlatformToolset reference in
:: the project file to VisualStudio 12.0, without this 32bit won't build.
copy C:\grr\vagrant\windows\libtsk4.1.3.vcxproj win32\libtsk\libtsk.vcxproj /y
cd %USERPROFILE%

:: Install pytsk
rd /s /q pytsk
del /f /q /s pytsk*
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://github.com/py4n6/pytsk/releases/download/20150111/pytsk-20150111.tgz', 'pytsk-20150111.tgz')"
7z e pytsk-20150111.tgz && 7z x pytsk-20150111.tar

cd pytsk
:: Fix references to VS2k8 in the build file
cmd /c ""C:\grr\vagrant\windows\64bitenv.bat" && devenv msvscpp\pytsk3.sln /upgrade"

:: Fix pytsk build settings to also target 64bit.
copy C:\grr\vagrant\windows\pytsk20150111.vcxproj msvscpp\pytsk3\pytsk3.vcxproj /y
del msvscpp\pytsk3\pytsk3.vcproj
copy C:\grr\vagrant\windows\libtalloc.vcxproj msvscpp\libtalloc\libtalloc.vcxproj /y
del msvscpp\libtalloc\libtalloc.vcproj
copy C:\grr\vagrant\windows\pytsk3.sln msvscpp\pytsk3.sln /y
cd %USERPROFILE%

cmd /c "C:\grr\vagrant\windows\64bit_pytsk.bat" || echo "64bit_pytsk.bat failed" && exit /b 1
cmd /c "C:\grr\vagrant\windows\32bit_pytsk.bat" || echo "32bit_pytsk.bat failed" && exit /b 1


