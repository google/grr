#!/bin/bash

# This script runs dygraphs through the Closure Compiler. This checks for
# errors (both in the JS and in the jsdoc) and flags type errors as WARNINGS.

# It outputs minified JS to a temp file. This should be ignored for now, until
# it's fully functional.

CLOSURE_COMPILER=node_modules/closure-compiler/lib/vendor/compiler.jar
BASE_JS=node_modules/obvious-closure-library/closure/goog/base.js
if [[ (! -f $CLOSURE_COMPILER) || (! -f $BASE_JS) ]]; then
  echo "Missing compiler.jar or base.js. Try running 'npm install'." 1>&2
  exit 1
fi

java -jar $CLOSURE_COMPILER \
 --compilation_level ADVANCED_OPTIMIZATIONS  \
 --warning_level VERBOSE  \
 --output_wrapper='(function() {%output%})();'  \
 --js $BASE_JS \
 --js=dashed-canvas.js \
 --js=dygraph-options.js \
 --js=dygraph-layout.js \
 --js=dygraph-canvas.js \
 --js=dygraph.js \
 --js=dygraph-utils.js \
 --js=dygraph-gviz.js \
 --js=dygraph-interaction-model.js \
 --js=dygraph-tickers.js \
 --js=dygraph-plugin-base.js \
 --js=plugins/annotations.js \
 --js=plugins/axes.js \
 --js=plugins/chart-labels.js \
 --js=plugins/grid.js \
 --js=plugins/legend.js \
 --js=plugins/range-selector.js \
 --js=dygraph-plugin-install.js \
 --js=dygraph-options-reference.js \
 --js=datahandler/datahandler.js \
 --js=datahandler/default.js \
 --js=datahandler/default-fractions.js \
 --js=datahandler/bars.js \
 --js=datahandler/bars-custom.js \
 --js=datahandler/bars-error.js \
 --js=datahandler/bars-fractions.js \
 --js=dygraph-exports.js \
 --externs dygraph-internal.externs.js  \
 --externs gviz-api.js  \
 --js_output_file=/tmp/out.js
