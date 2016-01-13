
:: Update the environment variale to make sure the protoc compiler is found.
set PROTOC=%USERPROFILE%/build/protoc.exe
set PROTO_SRC_ROOT=%USERPROFILE%/build/protobuf-2.6.1/src/

cmd /c ""C:\grr\vagrant\windows\64bitenv.bat" && cd \ && SET PYTHONPATH=. && python C:\grr\client\client_build.py --config=C:\grr\config\grr-server.yaml --arch amd64 --verbose build" || echo "64bit build failed" && exit /b 1

cmd /c ""C:\grr\vagrant\windows\64bitenv.bat" && cd \ && SET PYTHONPATH=. && python C:\grr\client\client_build.py --config=C:\grr\config\grr-server.yaml build_component grr\client\components\rekall_support\setup.py grr\executables\ " || echo "64bit rekall component build failed" && exit /b 1

cmd /c ""C:\grr\vagrant\windows\32bitenv.bat" && cd \ && SET PYTHONPATH=. && python C:\grr\client\client_build.py --config=C:\grr\config\grr-server.yaml --arch i386 --verbose build" || echo "32bit build failed" && exit /b 1

cmd /c ""C:\grr\vagrant\windows\32bitenv.bat" && cd \ && SET PYTHONPATH=. && python C:\grr\client\client_build.py --config=C:\grr\config\grr-server.yaml build_component grr\client\components\rekall_support\setup.py grr\executables\ " || echo "32bit rekall component  build failed" && exit /b 1
