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
 * @fileoverview Unit tests for goog.html.TrustedResourceUrl and its builders.
 */

goog.provide('goog.html.trustedResourceUrlTest');

goog.require('goog.html.TrustedResourceUrl');
goog.require('goog.i18n.bidi.Dir');
goog.require('goog.object');
goog.require('goog.string.Const');
goog.require('goog.testing.jsunit');

goog.setTestOnly('goog.html.trustedResourceUrlTest');


function testTrustedResourceUrl() {
  var url = 'javascript:trusted();';
  var trustedResourceUrl =
      goog.html.TrustedResourceUrl.fromConstant(goog.string.Const.from(url));
  var extracted = goog.html.TrustedResourceUrl.unwrap(trustedResourceUrl);
  assertEquals(url, extracted);
  assertEquals(url, trustedResourceUrl.getTypedStringValue());
  assertEquals(
      'TrustedResourceUrl{javascript:trusted();}', String(trustedResourceUrl));

  // URLs are always LTR.
  assertEquals(goog.i18n.bidi.Dir.LTR, trustedResourceUrl.getDirection());

  // Interface markers are present.
  assertTrue(trustedResourceUrl.implementsGoogStringTypedString);
  assertTrue(trustedResourceUrl.implementsGoogI18nBidiDirectionalString);
}


function testFormat_validFormatString() {
  // With scheme.
  assertValidFormat(goog.string.Const.from('httpS://www.gOOgle.com/'));
  // Scheme-relative.
  assertValidFormat(goog.string.Const.from('//www.google.com/'));
  // Origin with hyphen and port.
  assertValidFormat(goog.string.Const.from('//ww-w.google.com:1000/path'));
  // IPv6 origin.
  assertValidFormat(goog.string.Const.from('//[::1]/path'));
  // Path-absolute.
  assertValidFormat(goog.string.Const.from('/path'));
  assertValidFormat(goog.string.Const.from('/path/x'));
  assertValidFormat(goog.string.Const.from('/path#x'));
  assertValidFormat(goog.string.Const.from('/path?x'));
  // Mixed case.
  assertValidFormat(goog.string.Const.from('httpS://www.google.cOm/pAth'));
  assertValidFormat(goog.string.Const.from('about:blank'));
  assertValidFormat(goog.string.Const.from('about:blank#x'));
}


/**
 * Asserts that format with no arguments is allowed and results in a URL
 * with itself.
 * @param {!goog.string.Const} format
 */
function assertValidFormat(format) {
  var url = goog.html.TrustedResourceUrl.format(format, {});
  assertEquals(
      goog.string.Const.unwrap(format),
      goog.html.TrustedResourceUrl.unwrap(url));
}


function testFormat_args() {
  var url = goog.html.TrustedResourceUrl.format(
      goog.string.Const.from('/path/%{dir1}/%{dir2}?n1=v1%{opt_param}'), {
        'dir1': 'd%/?#=',
        'dir2': 2,
        'opt_param': goog.string.Const.from('n2=v2%/?#=')
      });
  assertEquals(
      '/path/d%25%2F%3F%23%3D/2?n1=v1n2=v2%/?#=',
      goog.html.TrustedResourceUrl.unwrap(url));

  // Only \w is permitted inside %{...}.
  var url = goog.html.TrustedResourceUrl.format(
      goog.string.Const.from('/path/%{!%{label}}%{foo'), {'label': 'value'});
  assertEquals(
      '/path/%{!value}%{foo', goog.html.TrustedResourceUrl.unwrap(url));
}


function testFormat_missingArgs() {
  var exception = assertThrows(function() {
    goog.html.TrustedResourceUrl.format(
        goog.string.Const.from('https://www.google.com/path/%{arg1}'),
        {'arg2': 'irrelevant'});
  });
  assertContains('no valid label mapping found', exception.message);
}


function testFormat_invalidFormatString() {
  // Invalid scheme.
  assertInvalidFormat(goog.string.Const.from('ftp://'));
  // Missing origin.
  assertInvalidFormat(goog.string.Const.from('https://'));
  assertInvalidFormat(goog.string.Const.from('https:///'));
  assertInvalidFormat(goog.string.Const.from('//'));
  assertInvalidFormat(goog.string.Const.from('///'));
  // Missing / after origin.
  assertInvalidFormat(goog.string.Const.from('https://google.com'));
  // Invalid char in origin.
  assertInvalidFormat(goog.string.Const.from('https://www.google%.com/'));
  assertInvalidFormat(goog.string.Const.from('https://www.google\\.com/'));
  assertInvalidFormat(
      goog.string.Const.from('https://user:password@www.google.com/'));
  // Two slashes, would allow origin to be set dynamically.
  assertInvalidFormat(goog.string.Const.from('//'));
  // Two slashes. IE allowed (allows?) '\' instead of '/'.
  assertInvalidFormat(goog.string.Const.from('/\\'));
  // Relative path.
  assertInvalidFormat(goog.string.Const.from('abc'));
  assertInvalidFormat(goog.string.Const.from('about:blankX'));
}


/**
 * Asserts that format with no arguments throws.
 * @param {!goog.string.Const} format
 */
function assertInvalidFormat(format) {
  var exception = assertThrows(goog.string.Const.unwrap(format), function() {
    goog.html.TrustedResourceUrl.format(format, {});
  });
  assertContains('Invalid TrustedResourceUrl format', exception.message);
}


function testFromConstants() {
  assertEquals('', goog.html.TrustedResourceUrl.unwrap(
      goog.html.TrustedResourceUrl.fromConstants([])));
  assertEquals('foo', goog.html.TrustedResourceUrl.unwrap(
      goog.html.TrustedResourceUrl.fromConstants([
        goog.string.Const.from('foo')
      ])));
  assertEquals('foobar', goog.html.TrustedResourceUrl.unwrap(
      goog.html.TrustedResourceUrl.fromConstants([
        goog.string.Const.from('foo'),
        goog.string.Const.from('bar')
      ])));
}


function testFormatWithParams() {
  var url = goog.html.TrustedResourceUrl.formatWithParams(
      goog.string.Const.from('https://example.com/'), {}, {'a': '&'});
  assertEquals('https://example.com/?a=%26', url.getTypedStringValue());

  url = goog.html.TrustedResourceUrl.formatWithParams(
      goog.string.Const.from('https://example.com/%{file}'), {'file': 'abc'},
      {'b': 1, 'c': null, 'd': undefined});
  assertEquals('https://example.com/abc?b=1', url.getTypedStringValue());

  url = goog.html.TrustedResourceUrl.formatWithParams(
      goog.string.Const.from('https://example.com/'), {}, {'a': ['x', 'y']});
  assertEquals('https://example.com/?a=x&a=y', url.getTypedStringValue());
}


/** @suppress {checkTypes} */
function testUnwrap() {
  var privateFieldName =
      'privateDoNotAccessOrElseTrustedResourceUrlWrappedValue_';
  var markerFieldName =
      'TRUSTED_RESOURCE_URL_TYPE_MARKER_GOOG_HTML_SECURITY_PRIVATE_';
  var propNames = goog.object.getKeys(
      goog.html.TrustedResourceUrl.fromConstant(goog.string.Const.from('')));
  assertContains(privateFieldName, propNames);
  assertContains(markerFieldName, propNames);
  var evil = {};
  evil[privateFieldName] = 'http://example.com/evil.js';
  evil[markerFieldName] = {};

  var exception =
      assertThrows(function() { goog.html.TrustedResourceUrl.unwrap(evil); });
  assertContains(
      'expected object of type TrustedResourceUrl', exception.message);
}
