// Copyright 2017 The Closure Library Authors. All Rights Reserved.
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
 * @fileoverview Tests for the textExtractor module.
 */

goog.module('goog.html.textExtractorTest');
goog.setTestOnly();

var testSuite = goog.require('goog.testing.testSuite');
var textExtractor = goog.require('goog.html.textExtractor');


/**
 * Verifies that the expected text is extracted from the HTML string.
 * @param {string} html The HTML string containing text mixed in HTML markup.
 * @param {string} expectedText The expected text extracted from the HTML
 * string.
 */
function assertExtractedTextEquals(html, expectedText) {
  var actualText = textExtractor.extractTextContent(html);
  if (textExtractor.isSupported()) {
    assertEquals(actualText, expectedText);
  } else {
    assertEquals(actualText, '');
  }
}

testSuite({
  testExtractTextContent_justText: function() {
    var html = 'Hello';
    assertExtractedTextEquals(html, html);
  },

  testExtractTextContent_basic: function() {
    var html = '<p>Hello</p>';
    var expectedText = 'Hello';
    assertExtractedTextEquals(html, expectedText);
  },

  testExtractTextContent_removesScript: function() {
    var html = '<p>Foo<script>Bar</script>Baz</p>';
    var expectedText = 'FooBaz';
    assertExtractedTextEquals(html, expectedText);
  },

  testExtractTextContent_blocks: function() {
    var html = '<div>Foo</div><div>Bar</div>';
    var expectedText = 'Foo\n\nBar';
    assertExtractedTextEquals(html, expectedText);
  },

  testExtractTextContent_extraNewlines: function() {
    var html = '<p>Foo</p>\n<p>Bar</p>';
    var expectedText = 'Foo\n\nBar';
    assertExtractedTextEquals(html, expectedText);
  },

  testExtractTextContent_inline: function() {
    var html = '<h1>Foo<span>Bar</span></h1>';
    var expectedText = 'FooBar';
    assertExtractedTextEquals(html, expectedText);
  },

  testExtractTextContent_complex: function() {
    var html = '<div>\n' +
        '  \n' +
        '  A\n' +
        '\n' +
        '  mind\n' +
        '\n' +
        '  needs books<br>as a sword needs a whetstone<p>' +  // no line break
        'if it is to <span style="display: block">keep</span> its edge.\n' +
        '  </p>\n' +
        '\n' +
        '</div>';
    var expectedText = 'A mind needs books\n' +
        'as a sword needs a whetstone\n' +
        'if it is to\n' +
        'keep\n' +
        'its edge.';
    assertExtractedTextEquals(html, expectedText);
  },

  testExtractTextContent_newlines: function() {
    var html = 'Hello\nWorld';
    var expectedText = 'Hello World';
    assertExtractedTextEquals(html, expectedText);
  },

  testExtractTextContent_br: function() {
    var html = 'Hello\n<br>World';
    var expectedText = 'Hello\nWorld';
    assertExtractedTextEquals(html, expectedText);
  },

  testExtractTextContent_brAndBlock: function() {
    var html = 'Hello\n\n<br>\n<p>World</p>';
    var expectedText = 'Hello\n\nWorld';
    assertExtractedTextEquals(html, expectedText);
  }
});
