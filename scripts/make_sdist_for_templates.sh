#!/bin/bash
# Build core and client sdists for client template building and upload them
# to cloud storage. This is useful for windows client template builds.

set -e
: ${BUCKET:="release-test.grr-response.com"}

# Check we are in the right directory running the right setup.py
grep "grr-response-core" setup.py
rm -rf dist/ || true
python setup.py sdist --no-make-docs --no-make-ui-files --formats=zip
gsutil rm "gs://${BUCKET}/grr-response-core-*.zip" || true
gsutil cp "dist/grr-response-core-*.zip" "gs://${BUCKET}/"

cd grr/config/grr-response-client
grep "grr-response-client" setup.py
rm -rf dist/ || true
python setup.py sdist --formats=zip
gsutil rm "gs://${BUCKET}/grr-response-client-*.zip" || true
gsutil cp "dist/grr-response-client-*.zip" "gs://${BUCKET}/"
cd -
