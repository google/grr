#!/bin/bash

set -e

function create_changelog() {
  if [[ -f debian/changelog ]]; then
    echo "Replacing debian/changelog with new changelog."
    rm debian/changelog
  fi
  pyscript="
import ConfigParser
config = ConfigParser.SafeConfigParser()
config.read('version.ini')
print('%s.%s.%s-%s' % (
    config.get('Version', 'major'),
    config.get('Version', 'minor'),
    config.get('Version', 'revision'),
    config.get('Version', 'release')))
"
  deb_version="$(python -c "${pyscript}")"
  debchange --create \
      --newversion "${deb_version}" \
      --package grr-server \
      --urgency low \
      --controlmaint \
      --distribution unstable \
      "Built by Travis CI at ${TRAVIS_COMMIT}"
}

# Sets environment variables to be used by debhelper.
function export_build_vars() {
  # Note that versions for the packages listed here can differ.
  export LOCAL_DEB_PYINDEX="${PWD}/local_pypi"
  export API_SDIST="$(ls sdists/grr-api-client-*.zip)"
  export TEST_SDIST="$(ls sdists/grr-response-test-*.zip)"
  export CLIENT_SDIST="$(ls sdists/grr-response-client-*.zip)"
  export TEMPLATES_SDIST="$(ls sdists/grr-response-templates-*.zip)"
  export SERVER_SDIST="$(ls sdists/grr-response-server-*.zip)"
}

create_changelog
export_build_vars
dpkg-buildpackage -us -uc
mkdir gcs_upload_dir && cp "${PWD}"/../grr-server* gcs_upload_dir
