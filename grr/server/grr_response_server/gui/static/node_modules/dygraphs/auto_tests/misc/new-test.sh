#!/bin/bash
#
# Run this to automatically create a new auto_test. Example:
#
#   ./auto_tests/misc/new_test.sh axis-labels
#
# This will produce a new file in auto_tests/tests/axis_labels.js including
#
#   var AxisLabelsTestCase = TestCase("axis-labels");
#   ...
#
# It will also add a reference to this file to auto_tests/misc/local.html.

set -o errexit
if [ -z $1 ]; then
  echo Usage: $0 test-case-name-with-dashes
  exit 1
fi

dashed_name=$1
underscore_name=$(echo $1 | sed 's/-/_/g')
camelCaseName=$(echo $1 | perl -pe 's/-([a-z])/uc $1/ge')
testCaseName=${camelCaseName}TestCase

test_file=auto_tests/tests/$underscore_name.js

if [ -f $test_file ]; then
  echo $test_file already exists
  exit 1
fi

cat <<END > $test_file;
/**
 * @fileoverview FILL THIS IN
 *
 * @author $(git config --get user.email) ($(git config --get user.name))
 */
var $testCaseName = TestCase("$dashed_name");

$testCaseName.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

$testCaseName.prototype.tearDown = function() {
};

$testCaseName.prototype.testNameGoesHere = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  ...
  assertEquals(1, 1);
};

END

perl -pi -e 'next unless /update_options.js/; print "  <script type=\"text/javascript\" src=\"../tests/'$underscore_name'.js\"></script>\n"' auto_tests/misc/local.html

echo Wrote test to $test_file
