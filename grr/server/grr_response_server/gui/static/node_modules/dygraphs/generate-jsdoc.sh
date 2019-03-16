#!/bin/bash
#
# Generates JSDoc in the /jsdoc dir. Clears any existing jsdoc there.

rm -rf jsdoc
echo Generating JSDoc...
java -jar jsdoc-toolkit/jsrun.jar \
  jsdoc-toolkit/app/run.js \
  -d=jsdoc -t=jsdoc-toolkit/templates/jsdoc \
  dygraph.js \
| tee /tmp/dygraphs-jsdocerrors.txt

if [ -s /tmp/dygraphs-jsdocerrors.txt ]; then
  echo Please fix any jsdoc errors/warnings before sending patches.
fi

chmod -R a+rX jsdoc

echo Done
