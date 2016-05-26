#!/bin/bash

set -e

INSTALL_USER="vagrant"

# Update the system
function system_update() {
  sudo softwareupdate --install --all
  # It's apparently no longer enough to just have the commandline tools
  # installed, you 'need' all of xcode, which requires the GUI to install.
  # http://stackoverflow.com/questions/13041525/osx-10-8-xcrun-no-such-file-or-directory
  # this is a dirty hack that works around that requirement, since xcrun is just
  # calling the compiler anyway:
  sudo xcode-select -switch /usr/bin
  sudo mv /usr/bin/xcrun /usr/bin/xcrun-orig
  cat > xcrun <<EOL
#!/bin/sh
\$@
EOL
  sudo mv xcrun /usr/bin/xcrun
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

# Install our python dependencies into a virtualenv that uses the new python
# version
function install_python_deps() {
  # pip and setuptools are installed by brew
  pip install --upgrade pip setuptools
  sudo -H pip install --upgrade virtualenv

  BUILDDIR="/home/${INSTALL_USER}/grrbuild"
  rm -rf "${BUILDDIR}" && mkdir "${BUILDDIR}"

  virtualenv -p /usr/local/bin/python2.7 "${BUILDDIR}/PYTHON_ENV"
  source "${BUILDDIR}/PYTHON_ENV/bin/activate"
  # pip takes a copy of the whole src tree, which includes the vagrant dir, so
  # it continues copying until it runs out of space. The workaround is to build
  # an sdist and install that.
  # https://github.com/google/grr/issues/373
  cd /grr
  python setup.py sdist --dist-dir="${BUILDDIR}/core" --no-make-docs --no-sync-artifacts
  cd -
  cd /grr/grr/config/grr-response-client/
  python setup.py sdist --dist-dir="${BUILDDIR}/client"
  cd -

  cd "${BUILDDIR}"
  pip install core/*.tar.gz
  pip install client/*.tar.gz
  cd -

  # pyinstaller fails to include protobuf because there is no __init__.py:
  # https://github.com/google/protobuf/issues/713
  touch "${BUILDDIR}/PYTHON_ENV/lib/python2.7/site-packages/google/__init__.py"
}

function install_python() {
  # Using --build-bottle is a (fairly futile) attempt to make our binaries work
  # on older Macs.  https://github.com/Homebrew/brew/issues/235
  brew install --build-bottle python
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
    brew install protobuf
    install_python
    install_python_deps
    ;;
esac
