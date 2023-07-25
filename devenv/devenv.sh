#!/usr/bin/env bash

cd "$(dirname "$0")"
python -c "import src; src.main()" "$@"
