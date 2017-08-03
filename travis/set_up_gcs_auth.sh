set -e

if [[ "$(which gcloud)" ]]; then
  echo "Google Cloud SDK already installed"
  gcloud version
else
  echo "Google Cloud SDK not found. Downloading.."
  # The linux sdk seems to work on Mac..¯\_(ツ)_/¯
  wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-116.0.0-linux-x86_64.tar.gz
  tar zxf google-cloud-sdk-116.0.0-linux-x86_64.tar.gz -C "${HOME}"
fi

# See https://docs.travis-ci.com/user/encrypting-files/
openssl aes-256-cbc -K "$encrypted_db009a5a71c6_key" \
  -iv "$encrypted_db009a5a71c6_iv" \
  -in travis/travis_uploader_service_account.json.enc \
  -out travis/travis_uploader_service_account.json -d

gcloud auth activate-service-account --key-file travis/travis_uploader_service_account.json
