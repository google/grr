#!/bin/bash
pip install -r requirements.txt

echo "Compiling proto files..."
echo "protoc version:"
protoc --version
cd proto
echo "Running make in proto dir..."
pwd
make
cd ..

echo "Compiling artifact files..."
cd artifacts
echo "Running make in artifacts dir..."
pwd
make
cd ..
