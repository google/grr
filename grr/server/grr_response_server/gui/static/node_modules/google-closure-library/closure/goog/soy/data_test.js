// Copyright 2014 The Closure Library Authors. All Rights Reserved.
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

goog.provide('goog.soy.dataTest');
goog.setTestOnly('goog.soy.dataTest');

goog.require('goog.html.SafeHtml');
goog.require('goog.html.SafeStyleSheet');
goog.require('goog.html.SafeUrl');
goog.require('goog.html.TrustedResourceUrl');
/** @suppress {extraRequire} */
goog.require('goog.soy.testHelper');
goog.require('goog.testing.jsunit');


function testToSafeHtml() {
  var html;

  html = example.unsanitizedTextTemplate().toSafeHtml();
  assertEquals(
      'I &lt;3 Puppies &amp; Kittens', goog.html.SafeHtml.unwrap(html));

  html = example.sanitizedHtmlTemplate().toSafeHtml();
  assertEquals('Hello <b>World</b>', goog.html.SafeHtml.unwrap(html));
}

function testToSafeUrl() {
  var url;

  url = example.sanitizedSmsUrlTemplate().toSafeUrl();
  assertEquals('sms:123456789', goog.html.SafeUrl.unwrap(url));

  url = example.sanitizedHttpUrlTemplate().toSafeUrl();
  assertEquals('https://google.com/foo?n=917', goog.html.SafeUrl.unwrap(url));
}

function testToSafeStyleSheet() {
  var url = example.sanitizedCssTemplate().toSafeStyleSheet();
  assertEquals('html{display:none}', goog.html.SafeStyleSheet.unwrap(url));
}

function testToTrustedResourceUrl() {
  var url;

  url = example.sanitizedTrustedResourceUriTemplate({}).toTrustedResourceUrl();
  assertEquals(
      'https://google.com/a.js', goog.html.TrustedResourceUrl.unwrap(url));
}
