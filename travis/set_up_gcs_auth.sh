set -e

# The linux sdk seems to work on Mac..¯\_(ツ)_/¯
wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-116.0.0-linux-x86_64.tar.gz
tar zxf google-cloud-sdk-116.0.0-linux-x86_64.tar.gz -C "${HOME}"

# See https://docs.travis-ci.com/user/encrypting-files/
openssl aes-256-cbc -K "${encrypted_38884bbe6880_key}" \
  -iv "${encrypted_38884bbe6880_iv}" \
  -in travis/travis_uploader_service_account.json.enc \
  -out travis/travis_uploader_service_account.json -d

gcloud auth activate-service-account --key-file travis/travis_uploader_service_account.json
