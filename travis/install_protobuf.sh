#!/bin/bash
# We need newer protobuf library than what precise has. Install into homedir to
# avoid the need for sudo, and cache the compiled result using travis caching.

set -e

VERSION=2.6.1

if [ ! -d "$HOME/protobuf/lib" ]; then
  wget "https://github.com/google/protobuf/releases/download/v${VERSION}/protobuf-${VERSION}.tar.gz"
  tar -xzvf "protobuf-${VERSION}.tar.gz"
  cd "protobuf-${VERSION}" && ./configure --prefix="$HOME/protobuf" && make && make install
else
  echo "Using cached proto directory $HOME/protobuf."
fi
