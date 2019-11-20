echo Installing GRR dependencies

mkdir C:\grr_deps || echo "Failed to create C:\grr_deps" && exit /b 1
cd C:\grr_deps

C:\Python36-x64\python.exe --version || echo "64bit python missing" && exit /b 1
C:\Python36\python.exe --version || echo "32bit python install failed" && exit /

:: Install Google Cloud SDK
echo Installing Google Cloud SDK
powershell -NoProfile -ExecutionPolicy unrestricted -Command "(new-object System.Net.WebClient).DownloadFile('https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-163.0.0-windows-x86_64.zip', 'C:\grr_deps\google-cloud-sdk-163.0.0-windows-x86_64.zip')"
C:\Python36-x64\python.exe -m "zipfile" -e C:\grr_deps\google-cloud-sdk-163.0.0-windows-x86_64.zip C:\grr_deps
C:\grr_deps\google-cloud-sdk\install.bat --quiet || echo "Google Cloud SDK installation failed" && exit /b 1

echo GRR dependency installation complete
