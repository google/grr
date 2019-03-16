// Copyright 2013 The Closure Library Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * @fileoverview Unit tests for goog.html.legacyconversions.
 */

goog.provide('goog.html.legacyconversionsTest');

goog.require('goog.html.SafeHtml');
goog.require('goog.html.SafeScript');
goog.require('goog.html.SafeStyle');
goog.require('goog.html.SafeStyleSheet');
goog.require('goog.html.SafeUrl');
goog.require('goog.html.TrustedResourceUrl');
goog.require('goog.html.legacyconversions');
goog.require('goog.testing.jsunit');

goog.setTestOnly('goog.html.legacyconversionsTest');


function testSafeHtmlFromString() {
  var html = '<div>irrelevant</div>';
  var safeHtml = goog.html.legacyconversions.safeHtmlFromString(html);
  assertEquals(html, goog.html.SafeHtml.unwrap(safeHtml));

  assertFunctionReports(goog.html.legacyconversions.safeHtmlFromString);
}


function testSafeScriptFromString() {
  var script = 'alert(1);';
  var safeScript = goog.html.legacyconversions.safeScriptFromString(script);
  assertEquals(script, goog.html.SafeScript.unwrap(safeScript));

  assertFunctionReports(goog.html.legacyconversions.safeScriptFromString);
}


function testSafeStyleFromString() {
  var style = 'color: red; width: 1em;';
  var safeStyle = goog.html.legacyconversions.safeStyleFromString(style);
  assertEquals(style, goog.html.SafeStyle.unwrap(safeStyle));

  assertFunctionReports(goog.html.legacyconversions.safeStyleFromString);
}


function testSafeStyleSheetFromString() {
  var styleSheet = 'P.special { color: red; background: url(http://test); }';
  var safeStyleSheet =
      goog.html.legacyconversions.safeStyleSheetFromString(styleSheet);
  assertEquals(styleSheet, goog.html.SafeStyleSheet.unwrap(safeStyleSheet));

  assertFunctionReports(goog.html.legacyconversions.safeStyleSheetFromString);
}


function testSafeUrlFromString() {
  var url = 'https://www.google.com';
  var safeUrl = goog.html.legacyconversions.safeUrlFromString(url);
  assertEquals(url, goog.html.SafeUrl.unwrap(safeUrl));

  assertFunctionReports(goog.html.legacyconversions.safeUrlFromString);
}


function testTrustedResourceUrlFromString() {
  var url = 'https://www.google.com/script.js';
  var trustedResourceUrl =
      goog.html.legacyconversions.trustedResourceUrlFromString(url);
  assertEquals(url, goog.html.TrustedResourceUrl.unwrap(trustedResourceUrl));

  assertFunctionReports(
      goog.html.legacyconversions.trustedResourceUrlFromString);
}


/**
 * Asserts that conversionFunction calls the report callback.
 * @param {function(string) : *} conversionFunction
 */
function assertFunctionReports(conversionFunction) {
  var reported = false;
  try {
    goog.html.legacyconversions.setReportCallback(function() {
      reported = true;
    });
    conversionFunction('irrelevant');
    assertTrue('Expected legacy conversion to be reported.', reported);
  } finally {
    goog.html.legacyconversions.setReportCallback(goog.nullFunction);
  }
}
