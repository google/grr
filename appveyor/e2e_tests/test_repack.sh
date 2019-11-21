#!/bin/bash
#
# Tests repacking of client templates using the 'grr_client_build' script.

set -ex

function fatal() {
  >&2 echo "Error: ${1}"
  exit 1
}

echo 'Client.labels: [repack-test]' > repack.yaml

grr_client_build --verbose \
  repack_multiple \
  --templates /usr/share/grr-server/grr-response-templates/templates/* \
  --repack_configs repack.yaml \
  --output_dir=.

declare -A client_installers
client_installers['Windows_64bit']='GRR_*_amd64.exe'
client_installers['Windows_64bit_debug']='dbg_GRR_*_amd64.exe'
client_installers['Ubuntu_64bit']='grr_*_amd64.deb'
client_installers['MacOS']='grr_*_amd64.pkg'

num_missing=0
for installer_name in "${!client_installers[@]}"; do
  installer_rgx="${client_installers[$installer_name]}"
  # shellcheck disable=SC2086
  if [[ -z "$(ls repack/${installer_rgx} 2>/dev/null)" ]]; then
    echo "${installer_name} installer was not repacked."
    num_missing=$((num_missing + 1))
  fi
done

if [[ "${num_missing}" -gt 0 ]]; then
  fatal 'Template repacking failed.'
else
  echo "Template repacking succeeded."
fi
