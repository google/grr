#!/bin/bash
# Helper script to release client templates.

set -e

VERSION=$1
RELEASE_NAME="grr-response-templates-${VERSION}"
RELEASE_TAR="${RELEASE_NAME}.tar.gz"
RELEASE_FILE="dist/${RELEASE_TAR}"
BUCKET="releases.grr-response.com"

md5fingerprint=$(md5sum "${RELEASE_FILE}" | cut -d" " -f1)

# Upload tarball, make public
gsutil cp "${RELEASE_FILE}" "gs://${BUCKET}/"
gsutil acl ch -u AllUsers:R "gs://${BUCKET}/${RELEASE_TAR}"

sed -i -e "s!</body></html>!<a href=\"${RELEASE_TAR}#md5=${md5fingerprint}\">${RELEASE_NAME}</a><br/>\n</body></html>!" index.html

gsutil cp index.html "gs://${BUCKET}/"
gsutil acl ch -u AllUsers:R "gs://${BUCKET}/index.html"

echo "Test install with:"
echo "pip install --allow-external grr-response-templates -f https://storage.googleapis.com/releases.grr-response.com/index.html grr-response-templates==${VERSION}"
