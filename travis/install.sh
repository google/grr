#!/bin/bash
set -e

# We frequently get network timeouts, try 3 times to install all the
# requirements
for i in {1..3}; do
  pip install -r requirements.txt && break || {
    if [[ $i -eq 3 ]]; then
      echo "Couldn't install python dependencies"
      exit 1
    fi
  }
done

echo "Compiling proto files..."
echo "protoc version:"
protoc --version
echo "Running make..."
pwd
python makefile.py

echo "Compiling artifact files..."
cd artifacts
echo "Running make in artifacts dir..."
pwd
python makefile.py
cd -
