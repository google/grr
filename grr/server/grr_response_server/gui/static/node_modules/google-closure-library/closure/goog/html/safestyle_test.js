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

/**
 * @fileoverview Unit tests for goog.html.SafeStyle and its builders.
 */

goog.provide('goog.html.safeStyleTest');

goog.require('goog.html.SafeStyle');
goog.require('goog.html.SafeUrl');
goog.require('goog.object');
goog.require('goog.string.Const');
goog.require('goog.testing.jsunit');

goog.setTestOnly('goog.html.safeStyleTest');


function testSafeStyle() {
  var style = 'width: 1em;height: 1em;';
  var safeStyle =
      goog.html.SafeStyle.fromConstant(goog.string.Const.from(style));
  var extracted = goog.html.SafeStyle.unwrap(safeStyle);
  assertEquals(style, extracted);
  assertEquals(style, safeStyle.getTypedStringValue());
  assertEquals('SafeStyle{' + style + '}', String(safeStyle));

  // Interface marker is present.
  assertTrue(safeStyle.implementsGoogStringTypedString);
}


/** @suppress {checkTypes} */
function testUnwrap() {
  var privateFieldName = 'privateDoNotAccessOrElseSafeStyleWrappedValue_';
  var markerFieldName = 'SAFE_STYLE_TYPE_MARKER_GOOG_HTML_SECURITY_PRIVATE_';
  var propNames = goog.object.getKeys(
      goog.html.SafeStyle.fromConstant(goog.string.Const.from('')));
  assertContains(privateFieldName, propNames);
  assertContains(markerFieldName, propNames);
  var evil = {};
  evil[privateFieldName] = 'width: expression(evil);';
  evil[markerFieldName] = {};

  var exception =
      assertThrows(function() { goog.html.SafeStyle.unwrap(evil); });
  assertContains('expected object of type SafeStyle', exception.message);
}


function testFromConstant_allowsEmptyString() {
  assertEquals(
      goog.html.SafeStyle.EMPTY,
      goog.html.SafeStyle.fromConstant(goog.string.Const.from('')));
}

function testFromConstant_throwsOnForbiddenCharacters() {
  assertThrows(function() {
    goog.html.SafeStyle.fromConstant(goog.string.Const.from('width: x<;'));
  });
  assertThrows(function() {
    goog.html.SafeStyle.fromConstant(goog.string.Const.from('width: x>;'));
  });
}


function testFromConstant_throwsIfNoFinalSemicolon() {
  assertThrows(function() {
    goog.html.SafeStyle.fromConstant(goog.string.Const.from('width: 1em'));
  });
}


function testFromConstant_throwsIfNoColon() {
  assertThrows(function() {
    goog.html.SafeStyle.fromConstant(goog.string.Const.from('width= 1em;'));
  });
}


function testEmpty() {
  assertEquals('', goog.html.SafeStyle.unwrap(goog.html.SafeStyle.EMPTY));
}


function testCreate() {
  assertCreateEquals(
      'background:url(i.png);margin:0;',
      {'background': goog.string.Const.from('url(i.png)'), 'margin': '0'});
}


function testCreate_allowsEmpty() {
  assertEquals(goog.html.SafeStyle.EMPTY, goog.html.SafeStyle.create({}));
}


function testCreate_skipsNull() {
  var style = goog.html.SafeStyle.create({'background': null});
  assertEquals(goog.html.SafeStyle.EMPTY, style);
}


function testCreate_allowsLengths() {
  assertCreateEquals(
      'padding:0 1px .2% 3.4em;',  // expected
      {'padding': '0 1px .2% 3.4em'});
}


function testCreate_allowsRgb() {
  assertCreateEquals(
      'color:rgb(10,20,30);',  // expected
      {'color': 'rgb(10,20,30)'});
  assertCreateEquals(
      'color:rgb(10%, 20%, 30%);',  // expected
      {'color': 'rgb(10%, 20%, 30%)'});
  assertCreateEquals(
      'background:0 5px rgb(10,20,30);',  // expected
      {'background': '0 5px rgb(10,20,30)'});
  assertCreateEquals(
      'background:rgb(10,0,0), rgb(0,0,30);',
      {'background': 'rgb(10,0,0), rgb(0,0,30)'});
}


function testCreate_allowsRgba() {
  assertCreateEquals(
      'color:rgba(10,20,30,0.1);',  // expected
      {'color': 'rgba(10,20,30,0.1)'});
  assertCreateEquals(
      'color:rgba(10%, 20%, 30%, .5);',  // expected
      {'color': 'rgba(10%, 20%, 30%, .5)'});
}


function testCreate_allowsScale() {
  assertCreateEquals(
      'transform:scale(.5, 2);',  // expected
      {'transform': 'scale(.5, 2)'});
}


function testCreate_allowsRotate() {
  assertCreateEquals(
      'transform:rotate(45deg);',  // expected
      {'transform': 'rotate(45deg)'});
}


function testCreate_allowsTranslate() {
  assertCreateEquals(
      'transform:translate(10px);',  // expected
      {'transform': 'translate(10px)'});
  assertCreateEquals(
      'transform:translateX(5px);',  // expected
      {'transform': 'translateX(5px)'});
}


function testCreate_allowsSafeUrl() {
  assertCreateEquals('background:url("http://example.com");', {
    'background': goog.html.SafeUrl.fromConstant(
        goog.string.Const.from('http://example.com'))
  });
}


function testCreate_allowsSafeUrlWithSpecialCharacters() {
  assertCreateEquals('background:url("http://example.com/\\"");', {
    'background': goog.html.SafeUrl.fromConstant(
        goog.string.Const.from('http://example.com/"'))
  });
  assertCreateEquals('background:url("http://example.com/%3c");', {
    'background': goog.html.SafeUrl.fromConstant(
        goog.string.Const.from('http://example.com/<'))
  });
  assertCreateEquals('background:url("http://example.com/;");', {
    'background': goog.html.SafeUrl.fromConstant(
        goog.string.Const.from('http://example.com/;'))
  });
}


function testCreate_allowsArray() {
  var url = goog.html.SafeUrl.fromConstant(
      goog.string.Const.from('http://example.com'));
  assertCreateEquals(
      'background:red url("http://example.com") repeat-y;',
      {'background': ['red', url, 'repeat-y']});
}


function testCreate_allowsUrl() {
  assertCreateEquals(
      'background:url(http://example.com);',
      {'background': 'url(http://example.com)'});
  assertCreateEquals(
      'background:url("http://example.com");',
      {'background': 'url("http://example.com")'});
  assertCreateEquals(
      'background:url( \'http://example.com\' );',
      {'background': 'url( \'http://example.com\' )'});
  assertCreateEquals(
      'background:url(http://example.com) red;',
      {'background': 'url(http://example.com) red'});
  assertCreateEquals(
      'background:url(' + goog.html.SafeUrl.INNOCUOUS_STRING + ');',
      {'background': 'url(javascript:alert)'});
  assertCreateEquals(
      'background:url(")");',  // Expected.
      {'background': 'url(")")'});
  assertCreateEquals(
      'background:url(" ");',  // Expected.
      {'background': 'url(" ")'});
  assertThrows(function() {
    goog.html.SafeStyle.create({'background': 'url(\'http://example.com\'"")'});
  });
  assertThrows(function() {
    goog.html.SafeStyle.create({'background': 'url("\\\\")'});
  });
  assertThrows(function() {
    goog.html.SafeStyle.create({'background': 'url(a""b)'});
  });
}


function testCreate_throwsOnForbiddenCharacters() {
  assertThrows(function() { goog.html.SafeStyle.create({'<': '0'}); });
  assertThrows(function() {
    goog.html.SafeStyle.create({'color': goog.string.Const.from('<')});
  });
}


function testCreate_values() {
  var valids = [
    '0', '0 0', '1px', '100%', '2.3px', '.1em', 'red', '#f00', 'red !important',
    '"Times New Roman"', "'Times New Roman'", '"Bold \'nuff"',
    '"O\'Connor\'s Revenge"'
  ];
  for (var i = 0; i < valids.length; i++) {
    var value = valids[i];
    assertCreateEquals(
        'background:' + value + ';',  // expected
        {'background': value});
  }

  var invalids = [
    '', 'expression(alert(1))', '"', '"\'"\'', goog.string.Const.from('red;')
  ];
  for (var i = 0; i < invalids.length; i++) {
    var value = invalids[i];
    assertThrows(function() {
      goog.html.SafeStyle.create({'background': value});
    });
  }
}


/**
 * Asserts that created SafeStyle matches expected value.
 * @param {string} expected
 * @param {!goog.html.SafeStyle.PropertyMap} style
 */
function assertCreateEquals(expected, style) {
  var style = goog.html.SafeStyle.create(style);
  assertEquals(expected, goog.html.SafeStyle.unwrap(style));
}


function testConcat() {
  var width =
      goog.html.SafeStyle.fromConstant(goog.string.Const.from('width: 1em;'));
  var margin = goog.html.SafeStyle.create({'margin': '0'});
  var padding = goog.html.SafeStyle.create({'padding': '0'});

  var style = goog.html.SafeStyle.concat(width, margin);
  assertEquals('width: 1em;margin:0;', goog.html.SafeStyle.unwrap(style));

  style = goog.html.SafeStyle.concat([width, margin]);
  assertEquals('width: 1em;margin:0;', goog.html.SafeStyle.unwrap(style));

  style = goog.html.SafeStyle.concat([width], [padding, margin]);
  assertEquals(
      'width: 1em;padding:0;margin:0;', goog.html.SafeStyle.unwrap(style));
}


function testConcat_allowsEmpty() {
  var empty = goog.html.SafeStyle.EMPTY;
  assertEquals(empty, goog.html.SafeStyle.concat());
  assertEquals(empty, goog.html.SafeStyle.concat([]));
  assertEquals(empty, goog.html.SafeStyle.concat(empty));
}
