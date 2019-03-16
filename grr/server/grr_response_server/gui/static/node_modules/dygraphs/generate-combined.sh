#!/bin/bash
# Generates a single JS file that's easier to include.

GetSources () {
  # Include dyraph-options-reference only if DEBUG environment variable is set.
  if [ ! -z "$DEBUG" ]; then
    maybe_options_reference=dygraph-options-reference.js
  else
    maybe_options_reference=''
  fi

  # This list needs to be kept in sync w/ the one in dygraph-dev.js
  # and the one in jsTestDriver.conf. Order matters, except for the plugins.
  for F in \
    polyfills/console.js \
    dashed-canvas.js \
    dygraph-options.js \
    dygraph-layout.js \
    dygraph-canvas.js \
    dygraph.js \
    dygraph-utils.js \
    dygraph-gviz.js \
    dygraph-interaction-model.js \
    dygraph-tickers.js \
    dygraph-plugin-base.js \
    plugins/*.js \
    dygraph-plugin-install.js \
    $maybe_options_reference \
    datahandler/datahandler.js \
    datahandler/default.js \
    datahandler/default-fractions.js \
    datahandler/bars.js \
    datahandler/bars-custom.js \
    datahandler/bars-error.js \
    datahandler/bars-fractions.js 
  do
      echo "$F"
  done
}

# Pack all the JS together.
CatSources () {
  GetSources \
  | xargs cat 
}

Copyright () {
  echo '/*! @license Copyright 2014 Dan Vanderkam (danvdk@gmail.com) MIT-licensed (http://opensource.org/licenses/MIT) */'
}

CatCompressed () {
  node_modules/uglify-js/bin/uglifyjs \
    $(GetSources | xargs) \
    --compress warnings=false \
    --mangle \
    --define DEBUG=false \
    --preamble "$(Copyright)" \
    $*
}

ACTION="${1:-update}"
case "$ACTION" in
ls)
  GetSources
  ;;
cat)
  Copyright
  CatSources
  ;;
cat-dev)
  DEBUG=true
  Copyright
  CatSources
  ;;
compress*|cat_compress*)
  CatCompressed
  ;;
update)
  CatCompressed --source-map dygraph-combined.js.map \
    > dygraph-combined.js
  chmod a+r dygraph-combined.js dygraph-combined.js.map
  ;;
*)
  echo >&2 "Unknown action '$ACTION'"
  exit 1
  ;;
esac
