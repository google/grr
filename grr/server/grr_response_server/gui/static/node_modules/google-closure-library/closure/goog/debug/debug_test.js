// Copyright 2008 The Closure Library Authors. All Rights Reserved.
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

goog.provide('goog.debugTest');
goog.setTestOnly('goog.debugTest');

goog.require('goog.debug');
goog.require('goog.debug.errorcontext');
goog.require('goog.structs.Set');
goog.require('goog.testing.jsunit');

function testMakeWhitespaceVisible() {
  assertEquals(
      'Hello[_][_]World![r][n]\n' +
          '[r][n]\n' +
          '[f][f]I[_]am[t][t]here![r][n]\n',
      goog.debug.makeWhitespaceVisible(
          'Hello  World!\r\n\r\n\f\fI am\t\there!\r\n'));
}

function testGetFunctionName() {
  // Trivial resolver that matches just a few names: a static function, a
  // constructor, and a member function.
  var resolver = function(f) {
    if (f === goog.debug.getFunctionName) {
      return 'goog.debug.getFunctionName';
    } else if (f === goog.structs.Set) {
      return 'goog.structs.Set';
    } else if (f === goog.structs.Set.prototype.getCount) {
      return 'goog.structs.Set.getCount';
    } else {
      return null;
    }
  };
  goog.debug.setFunctionResolver(resolver);

  assertEquals(
      'goog.debug.getFunctionName',
      goog.debug.getFunctionName(goog.debug.getFunctionName));
  assertEquals(
      'goog.structs.Set', goog.debug.getFunctionName(goog.structs.Set));
  var set = new goog.structs.Set();
  assertEquals(
      'goog.structs.Set.getCount', goog.debug.getFunctionName(set.getCount));

  // This function is matched by the fallback heuristic.
  assertEquals(
      'testGetFunctionName', goog.debug.getFunctionName(testGetFunctionName));

  goog.debug.setFunctionResolver(null);
}


/**
 * Asserts that a substring can be found in a specified text string.
 *
 * @param {string} substring The substring to search for.
 * @param {string} text The text string to search within.
 */
function assertContainsSubstring(substring, text) {
  assertNotEquals(
      'Could not find "' + substring + '" in "' + text + '"', -1,
      text.search(substring));
}


function testDeepExpose() {
  var a = {};
  var b = {};
  var c = {};
  a.ancestor = a;
  a.otherObject = b;
  a.otherObjectAgain = b;
  b.nextLevel = c;
  // Add Uid to a before deepExpose.
  var aUid = goog.getUid(a);

  var deepExpose = goog.debug.deepExpose(a);

  assertContainsSubstring(
      'ancestor = ... reference loop detected .id=' + aUid + '. ...',
      deepExpose);

  assertContainsSubstring('otherObjectAgain = {', deepExpose);

  // Make sure we've reset Uids after the deepExpose call.
  assert(goog.hasUid(a));
  assertFalse(goog.hasUid(b));
  assertFalse(goog.hasUid(c));
}


function testEnhanceErrorWithContext() {
  var err = 'abc';
  var context = {firstKey: 'first', secondKey: 'another key'};
  var errorWithContext = goog.debug.enhanceErrorWithContext(err, context);
  assertObjectEquals(
      context, goog.debug.errorcontext.getErrorContext(errorWithContext));
}


function testEnhanceErrorWithContext_combinedContext() {
  var err = new Error('abc');
  goog.debug.errorcontext.addErrorContext(err, 'a', '123');
  var context = {b: '456', c: '789'};
  var errorWithContext = goog.debug.enhanceErrorWithContext(err, context);
  assertObjectEquals(
      {a: '123', b: '456', c: '789'},
      goog.debug.errorcontext.getErrorContext(errorWithContext));
}


function testFreeze_nonDebug() {
  if (goog.DEBUG && typeof Object.freeze == 'function') return;
  var a = {};
  assertEquals(a, goog.debug.freeze(a));
  a.foo = 42;
  assertEquals(42, a.foo);
}


function testFreeze_debug() {
  if (goog.DEBUG || typeof Object.freeze != 'function') return;
  var a = {};
  assertEquals(a, goog.debug.freeze(a));
  try {
    a.foo = 42;
  } catch (expectedInStrictMode) {
  }
  assertUndefined(a.foo);
}
