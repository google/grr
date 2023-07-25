#!/usr/bin/env bash

set -e

THIS_DIR="$(cd "$(dirname "$0")" && pwd)"

USAGE="
Fleetspeak server startup script.
Usage: $0 admin|(frontend PUBLIC_IP)
"

function main() {
  local public_ip=
  local component=

  case "$1" in
    -h|--help)
      echo "$USAGE"
      exit 1
      ;;
    admin)
      component=admin
      shift
      ;;
    frontend)
      component=frontend
      public_ip=$2
      [[ -n "$public_ip" ]] || {
        echo "The frontend needs a public IP provided. See --help"
        exit 1
      }
      sed -i "s/%PUBLIC_IP%/$public_ip/g" \
        "$THIS_DIR/config/frontend.components.config"
      shift
      ;;
    *)
      echo "Unknown arg: $1. See --help"
      exit 1
      ;;
  esac

  "$THIS_DIR/fleetspeak-server" \
    -components_config "$THIS_DIR/config/$component.components.config" \
    -services_config "$THIS_DIR/config/services.config" \
    -logtostderr \
    "$@"
}

main "$@"
