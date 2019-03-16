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


goog.provide('goog.html.safeHtmlFormatterTest');
goog.setTestOnly('goog.html.safeHtmlFormatterTest');

goog.require('goog.html.SafeHtml');
goog.require('goog.html.SafeHtmlFormatter');
goog.require('goog.string');
goog.require('goog.testing.PropertyReplacer');
goog.require('goog.testing.jsunit');


var stubs;


function setUp() {
  stubs = new goog.testing.PropertyReplacer();
}


function tearDown() {
  stubs.reset();
}


function testFormat() {
  var formatter = new goog.html.SafeHtmlFormatter();
  assertSameHtml('a <b class="bold">&lt;bold&gt;</b> statement',
      formatter.format(goog.string.subs('a %s<bold>%s %s',
          formatter.startTag('b', {'class': 'bold'}),
          formatter.endTag('b'),
          formatter.text('statement'))));
}


function testFormatWithGetMsg() {
  var formatter = new goog.html.SafeHtmlFormatter();
  assertSameHtml('a <b class="bold">&lt;bold&gt;</b> statement',
      formatter.format(goog.getMsg('a {$startBold}<bold>{$endBold} {$type}', {
        'startBold': formatter.startTag('b', {'class': 'bold'}),
        'endBold': formatter.endTag('b'),
        'type': formatter.text('statement')
      })));
}


function testFormatWithText() {
  var formatter = new goog.html.SafeHtmlFormatter();
  // Escapes format.
  assertSameHtml('dinner &lt;3', formatter.format('dinner <3'));
  // Escapes .text().
  assertSameHtml('dinner &lt;3', formatter.format(formatter.text('dinner <3')));
}


function testFormatWithSafeHtml() {
  var formatter = new goog.html.SafeHtmlFormatter();
  assertSameHtml('User input: <b>abc</b>', formatter.format('User input: ' +
      formatter.safeHtml(goog.html.SafeHtml.create('b', {}, 'abc'))));
}


function testFormatWithInternalMarkers() {
  var formatter = new goog.html.SafeHtmlFormatter();

  // Immunity against something looking like our marker.
  assertSameHtml('{SafeHtmlFormatter:abc}',
      formatter.format('{SafeHtmlFormatter:abc}'));
  assertSameHtml('{SafeHtmlFormatter:<br>}',
      formatter.format('{SafeHtmlFormatter:' + formatter.startTag('br') + '}'));

  // If an attacker steals our random marker and we format his input using
  // .text() then we will get back his input (the random marker), not the tag.
  var br = formatter.startTag('br');
  var attackerInput = br;
  assertSameHtml(goog.string.htmlEscape(attackerInput) + '<br>',
      formatter.format(formatter.text(attackerInput) + br));
}


function testInvalidTag() {
  assertThrows(function() {
    formatter.startTag('a onclick="alert(1);"');
  });
  assertThrows(function() {
    formatter.startTag('a', {'onclick': 'alert(1);'});
  });
  assertThrows(function() {
    formatter.startTag('script');
  });
  assertThrows(function() {
    formatter.endTag('script');
  });
}


function testFormatBalancingTags() {
  var formatter = new goog.html.SafeHtmlFormatter();

  // Void tags are OK.
  formatter.format(formatter.startTag('br'));

  // Balanced tags are OK.
  formatter.format(formatter.startTag('b') + formatter.endTag('b'));

  // Order of calling startTag and endTag doesn't matter.
  var endTag = formatter.endTag('b');
  var startTag = formatter.startTag('b');
  formatter.format(startTag + endTag);

  // Unbalanced tags throw.
  assertThrows(function() {
    formatter.format(formatter.endTag('b') + formatter.startTag('b'));
  });

  // Unclosed tags throw.
  assertThrows(function() {
    formatter.format(formatter.startTag('b'));
  });

  // Unopened tags throw.
  assertThrows(function() {
    formatter.format(formatter.endTag('b'));
  });
}


function testDetectDoubleEscaping() {
  stubs.set(goog.string, 'DETECT_DOUBLE_ESCAPING', true);
  stubs.set(goog.string, 'ALL_RE_', /[\x00&<>"'e]/);
  var formatter = new goog.html.SafeHtmlFormatter();
  assertSameHtml('t&#101;st', formatter.format(formatter.text('test')));
}


function assertSameHtml(expected, html) {
  assertEquals(expected, goog.html.SafeHtml.unwrap(html));
}
