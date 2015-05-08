cmd /c ""C:\grr\vagrant\windows\64bitenv.bat" && cd \ && SET PYTHONPATH=. && python C:\grr\client\client_build.py --config=C:\grr\config\grr-server.yaml --arch amd64 --verbose build" || echo "64bit build failed" && exit /b 1
cmd /c ""C:\grr\vagrant\windows\32bitenv.bat" && cd \ && SET PYTHONPATH=. && python C:\grr\client\client_build.py --config=C:\grr\config\grr-server.yaml --arch i386 --verbose build" || echo "32bit build failed" && exit /b 1

