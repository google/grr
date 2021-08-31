#!/bin/bash

set -ex

function create_changelog() {
  if [[ -f debian/changelog ]]; then
    echo "Replacing debian/changelog with new changelog."
    rm debian/changelog
  fi
  pyscript="
import configparser
config = configparser.ConfigParser()
config.read('version.ini')
print('%s.%s.%s-%s' % (
    config.get('Version', 'major'),
    config.get('Version', 'minor'),
    config.get('Version', 'revision'),
    config.get('Version', 'release')))
"
  deb_version="$(python3 -c "${pyscript}")"
  debchange --create \
      --newversion "${deb_version}" \
      --package grr-server \
      --urgency low \
      --controlmaint \
      --distribution unstable \
      "Built by GitHub Actions at ${GITHUB_SHA}"
}

# Sets environment variables to be used by debhelper.
function export_build_vars() {
  # Note that versions for the packages listed here can differ.
  export LOCAL_DEB_PYINDEX="${PWD}/local_pypi"
  export API_SDIST="$(ls local_pypi | grep -e 'grr-api-client-.*\.zip')"
  export CLIENT_BUILDER_SDIST="$(ls local_pypi | grep -e 'grr-response-client-builder.*\.zip')"
  export TEMPLATES_SDIST="$(ls local_pypi | grep -e 'grr-response-templates-.*\.zip')"
  export SERVER_SDIST="$(ls local_pypi | grep -e 'grr-response-server-.*\.zip')"
}

create_changelog
export_build_vars
rm -f ../grr-server_*.tar.gz
rm -rf gcs_upload_dir
dpkg-buildpackage -us -uc
mkdir gcs_upload_dir && cp ../grr-server_* gcs_upload_dir
