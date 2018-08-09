#!/bin/bash
# We need newer protobuf library than what precise has. Install into homedir to
# avoid the need for sudo, and cache the compiled result using travis caching.

set -e

OS=''
case "$(uname -s)" in
  'Linux')
    OS='linux'
    ;;
  'Darwin')
    OS='osx'
    ;;
esac

OS=${1:-"${OS}"}

if [[ -z "${OS}" ]]; then
  echo 'Failed to detect OS.'
  exit 1
fi

VERSION=3.3.0
ARCH=$(uname -m)
# Get arch in the format that the protobuf urls use
if [ "${ARCH}" == "i686" ]; then
  ARCH="x86_32"
fi

if [ ! -d "${HOME}/protobuf/bin" ]; then
  # CWD is grr src checked out by travis.
  cwd=$(pwd)
  mkdir -p "${HOME}/protobuf"
  cd "${HOME}/protobuf"
  wget --quiet "https://github.com/google/protobuf/releases/download/v${VERSION}/protoc-${VERSION}-${OS}-${ARCH}.zip"
  unzip "protoc-${VERSION}-${OS}-${ARCH}.zip"
  cd "${cwd}"
else
  echo "Using cached proto directory $HOME/protobuf"
fi
