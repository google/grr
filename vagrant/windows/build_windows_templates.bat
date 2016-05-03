:: Update the environment variale to make sure the protoc compiler is found.
:: We dont need to run special compilers so just enter the virtualenv and build. Python will already find its own MSVC for python compilers.

cmd /c ""C:\PYTHON_64\Scripts\activate" && grr_client_build --arch amd64 --verbose build --output \grr\executables\" || echo "64bit build failed" && exit /b 1

cmd /c ""C:\PYTHON_64\Scripts\activate" && grr_client_build  build_components --output \grr\grr\executables\components\ " || echo "64bit rekall component build failed" && exit /b 1

cmd /c ""C:\PYTHON_32\Scripts\activate" && grr_client_build --arch i386 --verbose build --output \grr\executables\" || echo "32bit build failed" && exit /b 1

cmd /c ""C:\PYTHON_32\Scripts\activate" && grr_client_build build_components --output \grr\executables\components\ " || echo "32bit rekall component  build failed" && exit /b 1
