#!/usr/bin/env bash

cd "$(dirname "$0")"
PYTHONDONTWRITEBYTECODE=1 python -c "import src; src.main()" "$@"
