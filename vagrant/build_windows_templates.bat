net use x: /delete
net use x: /persistent:no \\VBOXSVR\host
x:
C:\python27\python.exe grr\client\client_build.py --config grr/config/grr-server.yaml  --arch amd64 --verbose build
C:\python27.32\python.exe grr\client\client_build.py --config grr/config/grr-server.yaml --arch i386 --verbose build
