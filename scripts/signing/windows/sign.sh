#!/bin/bash
#
# Build and sign windows installers
# Requires osslsigncode from http://sourceforge.net/projects/osslsigncode/
# Tested with osslsigncode-1.7.1
#
# TODO(user): this should be replaced with python code in client_build.

BUILD_COMMAND=grr/client/client_build.py
E_DIR_MISSING=1
E_BAD_CERT=2
E_BAD_KEY=3
E_BAD_RETURN_CODE=4
E_SIGNING_ERROR=5
E_NOT_ENOUGH_PARAMS=6


err() {
  echo -e "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $@" >&2
}

function chk_cmd()
{
  CMD=$*;
  ${CMD};
  RETVAL=$?
  if [ $RETVAL -ne 0 ]; then
    err "Bad return code from: $CMD";
    exit "${E_BAD_RETURN_CODE}"
  fi
};

sign_exes() {
  for filename in ${1}/*.exe; do
    echo "Signing ${filename}"

# osslsigncode doesn't play nicely with passwords on stdin and we don't want to
# use the -pass commandline parameter that will show up in process listings.
# Workaround with expect.
expect -<<EOD
spawn osslsigncode sign -certs "${certfile}" -key "${keyfile}" -n "${application}" -t http://timestamp.verisign.com/scripts/timstamp.dll -in ${filename} -out ${filename}.signed
expect "Enter PEM pass phrase:"
send "${password}\r"
wait
EOD

    if [ -f ${filename}.signed ]; then
      mv ${filename}.signed ${filename}
    else
      err "Signing error, ${filename}.signed missing"
      exit "${E_SIGNING_ERROR}"
    fi

    chk_cmd osslsigncode verify -in ${filename}

  done
}

rebuild_zips() {
  zipfile=${1}
  zipfile_base=`basename ${zipfile}`
  outdir=${2}
  echo Removing ${zipfile}
  chk_cmd rm -f ${zipfile}

  chk_cmd cd "${zipfile}.temp"

  echo Making new zipfile ${zipfile}
  chk_cmd zip -r ../${zipfile_base} *
  cd -

  echo Removing ${zipfile}.temp
  chk_cmd rm -rf "${zipfile}.temp"
}

function build_and_sign() {
  arch=${1}
  contextname=${2}

  echo -e "\nRunning deploy for ${contextname} ${arch}"
  ${BUILD_COMMAND} \
    --config ${configfile} \
    --platform windows \
    --context "${contextname} Context" \
    --arch ${arch} deploy \
    --templatedir ${inputdir} \
    --outputdir ${directory}

  # We don't know what name the client_build script chose for the output file,
  # but we know it's the only .deployed file in the directory since we delete
  # them once repacking is finished.
  client=( ${directory}/*${arch}.exe.deployed )
  unzip "${client}" -d "${client}.temp"

  chk_cmd sign_exes "${client}.temp" ${password}
  chk_cmd rebuild_zips "${client}" ${directory}

  echo -e "\nRepacking ${client}"
  ${BUILD_COMMAND} \
    --config ${configfile} \
    --platform windows \
    --context "${contextname} Context" \
    --arch ${arch} repack \
    --template ${client} \
    --outputdir ${directory}

  chk_cmd rm ${client}

  # Now build a debug version
  echo -e "\nRunning debug deploy for ${contextname} ${arch}"
  ${BUILD_COMMAND} \
    --config ${configfile} \
    --platform windows \
    --context "${contextname} Context" \
    --arch ${arch} deploy \
    --debug_build \
    --templatedir ${inputdir} \
    --outputdir ${directory}
  dbg_client=( ${directory}/*${arch}.exe.deployed )
  unzip "${dbg_client}" -d "${dbg_client}.temp"

  chk_cmd sign_exes "${dbg_client}.temp" ${password}
  chk_cmd rebuild_zips "${dbg_client}" ${directory}

  echo -e "\nRepacking ${dbg_client}"
  ${BUILD_COMMAND} \
    --config ${configfile} \
    --platform windows \
    --context "${contextname} Context" \
    --arch ${arch} repack \
    --debug_build \
    --template ${dbg_client} \
    --outputdir ${directory}

  chk_cmd rm ${dbg_client}
}


function usage() {
  echo -e "\nUsage: sign.sh [template_file_dir] [certfile.spc] [keyfile.pvk] [application name] [config file] [context names ...]\n\n\ne.g. PYTHONPATH=. ./grr/scripts/signing/windows/sign.sh ~/templates/ mycerts.spc mykey.pvk MyCompany grr_server.yaml Corp Prod Special" >&2
}

while getopts "h?" opt; do
  case "$opt" in
  h|\?)
    usage
    exit 0
    ;;
  esac
done

if [ $# -lt 6 ]; then
  usage
  exit "${E_NOT_ENOUGH_PARAMS}"
fi

inputdir=${@:$OPTIND:1}
certfile=${@:$OPTIND+1:1}
keyfile=${@:$OPTIND+2:1}
application=${@:$OPTIND+3:1}
configfile=${@:$OPTIND+4:1}

shift $((OPTIND+4))
context_names=${@}

if [ ! -d "${inputdir}" ]; then
  err "Directory ${1} not found"
  exit "${E_DIR_MISSING}"
fi

if [[ $certfile != *.spc ]]; then
  err "Certfile ${certfile} must end in .spc"
  exit "${E_BAD_CERT}"
fi

if [[ $keyfile != *.pvk ]]; then
  err "Keyfile ${keyfile} must end in .pvk"
  exit "${E_BAD_KEY}"
fi

echo -e "\nProceeding to sign client templates in ${inputdir} with cert ${certfile} and key ${keyfile}\n"

directory="build/windows_`date +'%Y-%m-%dT%H:%M:%S%z'`"
chk_cmd mkdir -p "${directory}"

read -s -p "Enter password for ${keyfile}:" password

for contextname in ${context_names}; do
  chk_cmd build_and_sign amd64 ${contextname}
  chk_cmd build_and_sign i386 ${contextname}
done

# Sign all of the installers
echo -e "\n\nSigning all installers in ${directory}\n"
chk_cmd sign_exes "${directory}" ${password}

password="nothing"

echo -e "Done.\nSigned installers in ${directory}\n"
