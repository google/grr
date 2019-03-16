// Copyright 2016 The Closure Library Authors. All Rights Reserved.
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

goog.provide('goog.net.streams.Base64StreamDecoderTest');
goog.setTestOnly('goog.net.streams.Base64StreamDecoderTest');

goog.require('goog.net.streams.Base64StreamDecoder');
goog.require('goog.testing.asserts');
goog.require('goog.testing.jsunit');

// Static test data
// clang-format off
var tests = [
  '', '',
  'f', 'Zg==',
  'fo', 'Zm8=',
  'foo', 'Zm9v',
  'foob', 'Zm9vYg==',
  'fooba', 'Zm9vYmE=',
  'foobar', 'Zm9vYmFy',
  'foobar', '  Zm  9v \t Ym \n Fy  ',  // whitespaces will be ignored

  '\xfb\xff\xbf\x4d', '+/+/TQ==',
  '\xfb\xff\xbf\x4d', '-_-_TQ..',  // websafe

  // non-ascii characters
  '\xe4\xb8\x80\xe4\xba\x8c\xe4\xb8\x89\xe5\x9b\x9b\xe4\xba\x94\xe5' +
      '\x85\xad\xe4\xb8\x83\xe5\x85\xab\xe4\xb9\x9d\xe5\x8d\x81',
  '5LiA5LqM5LiJ5Zub5LqU5YWt5LiD5YWr5Lmd5Y2B'
];
// clang-format on

/**
 * @param {string} s The string
 * @return {!Array<number>} The UTF-16 codes of the characters of the string.
 */
function stringCodes(s) {
  codes = [];
  for (var i = 0; i < s.length; i++) {
    codes.push(s.charCodeAt(i));
  }
  return codes;
}

function testSingleMessage() {
  var decoder = new goog.net.streams.Base64StreamDecoder();

  for (var i = 0; i < tests.length; i += 2) {
    var decoded = decoder.decode(tests[i + 1]);
    if (tests[i]) {
      assertElementsEquals(stringCodes(tests[i]), decoded);
    } else {
      assertNull(decoded);
    }
  }
}

function testBadMessage() {
  var decoder = new goog.net.streams.Base64StreamDecoder();

  assertThrows(function() { decoder.decode('badchar!'); });
  assertFalse(decoder.isInputValid());

  // decoder already invalidated
  assertThrows(function() { decoder.decode('abc'); });
  assertFalse(decoder.isInputValid());
}

function testMessagesInChunks() {
  var decoder = new goog.net.streams.Base64StreamDecoder();

  assertNull(decoder.decode('Zm'));
  assertNull(decoder.decode('9'));
  assertElementsEquals(stringCodes('foobar'), decoder.decode('vYmFyZm'));
  assertElementsEquals(stringCodes('foo'), decoder.decode('9v'));
  assertElementsEquals(stringCodes('barfoo'), decoder.decode('YmFyZm9v'));
  assertTrue(decoder.isInputValid());
}
