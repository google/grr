#!/bin/bash
which phantomjs > /dev/null
if [ $? != 0 ]; then
  echo You must install phantomjs to use command-line testing.
  echo Visit http://www.phantomjs.org/ to get it.
  echo
  echo OR open auto_tests/misc/local.html in a browser.
  echo OR follow the instructions in auto_tests/README
  exit 1
fi

# Don't run tests if the documentation doesn't parse.
./generate-documentation.py > /dev/null
if [ $? != 0 ]; then
  echo Failed to generate documentation. Fix this before running tests.
  exit 1
fi

phantomjs phantom-driver.js $* | tee /tmp/test-results.txt
trap "rm -f /tmp/test-results.txt" EXIT
if grep -q 'FAIL' /tmp/test-results.txt; then
  echo One or more tests failed.
  exit 1
fi
