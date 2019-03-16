#!/bin/bash
#
# Compiles pertinent Closure library files.

# TODO(joeltine): Make strictMissingRequire an error when 
# @suppress {missingRequire} works for it.

java -Xmx1G -jar ../closure-compiler-1.0-SNAPSHOT.jar \
  -O ADVANCED \
  --warning_level VERBOSE \
  --jscomp_error='*' \
  --jscomp_off=strictMissingRequire \
  --jscomp_off=inferredConstCheck \
  --jscomp_off=extraRequire \
  --jscomp_off=deprecated \
  --jscomp_off=lintChecks \
  --jscomp_off=analyzerChecks \
  --jscomp_warning=unusedLocalVariables \
  --js='**.js' \
  --js='!**_test.js' \
  --js='!**_perf.js' \
  --js='!**tester.js' \
  --js='!**promise/testsuiteadapter.js' \
  --js='!**osapi/osapi.js' \
  --js='!**svgpan/svgpan.js' \
  --js='!**alltests.js' \
  --js='!**node_modules**.js' \
  --js='!**protractor_spec.js' \
  --js='!**protractor.conf.js' \
  --js='!**browser_capabilities.js' \
  --js='!./doc/**.js' \
  --js_output_file=$(mktemp);
