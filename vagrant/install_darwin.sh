#!/bin/bash

# This script installs all dependencies and is run as part of vagrant
# provisioning. It is designed to run on OS X 10.8.

set -e
set -x

INSTALL_USER="vagrant"

function system_update() {
  sudo xcode-select -switch /usr/bin
}

# Install homebrew
function install_homebrew() {
  # Use /dev/null as stdin to disable prompting during install
  # This script dies if it is run a second time so || true
  ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" </dev/null || true
  # Need new curl to be able download things from modern SSL websites.
  brew install curl
  # Brew doctor complains that you are using an old version of OS X.
  brew doctor || true
  brew update
  brew install makedepend
}

function install_proto_compiler {
  VERSION=3.2.0
  PROTO_DIR=${HOME}/protobuf
  if [ ! -d "${PROTO_DIR}/bin" ]; then
    cwd=$(pwd)
    mkdir -p "${PROTO_DIR}"
    cd "${PROTO_DIR}"
    curl -OfsSL "https://github.com/google/protobuf/releases/download/v${VERSION}/protoc-${VERSION}-osx-x86_64.zip"
    unzip "protoc-${VERSION}-osx-x86_64.zip"
    chmod -R a+rx "${PROTO_DIR}"
    echo export PROTOC="${PROTO_DIR}/bin/protoc" >> "${HOME}/.bash_profile"
    cd "${cwd}"
  else
    echo "protoc already installed in ${PROTO_DIR}"
  fi
}


function xcrun_hack() {
  # It's apparently no longer enough to just have the commandline tools
  # installed, you 'need' all of xcode, which requires the GUI to install.
  # http://stackoverflow.com/questions/13041525/osx-10-8-xcrun-no-such-file-or-directory
  # this is a dirty hack that works around that requirement, since xcrun is just
  # calling the compiler anyway. We need it because without it setup.py thinks
  # your gcc is broken and you get "RuntimeError: autoconf error".
  sudo mv /usr/bin/xcrun /usr/bin/xcrun-orig
  cat > xcrun <<EOL
#!/bin/sh
\$@
EOL
  sudo mv xcrun /usr/bin/xcrun
  sudo chmod a+x /usr/bin/xcrun
}

# Install our python dependencies into a virtualenv that uses the new python
# version
function install_python_deps() {
  # pip and setuptools are installed by brew
  /usr/local/bin/python2.7 -m pip install --upgrade pip setuptools
  sudo -H /usr/local/bin/python2.7 -m pip install --upgrade virtualenv
}

function install_python() {
  # Using --build-bottle is a (fairly futile) attempt to make our binaries work
  # on older Macs.  https://github.com/Homebrew/brew/issues/235
  brew install --build-bottle python
  brew postinstall python
  # Brew recommends adding its libraries to your python path like this:
  mkdir -p "${HOME}/Library/Python/2.7/lib/python/site-packages"
  echo 'import site; site.addsitedir("/usr/local/lib/python2.7/site-packages")' >> "${HOME}/Library/Python/2.7/lib/python/site-packages/homebrew.pth"
}

# We want to run unprivileged since that's what homebrew expects, but vagrant
# provisioning runs as root.
case $EUID in
  0)
    sudo -u "$INSTALL_USER" -i "$0"  # script calling itself as the vagrant user
    ;;
  *)
    system_update
    install_homebrew
    install_proto_compiler
    brew install libffi
    install_python
    install_python_deps
    xcrun_hack
    echo Install completed sucessfully.
    ;;
esac
