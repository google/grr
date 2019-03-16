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

goog.provide('goog.reflectTest');
goog.setTestOnly('goog.reflectTest');

goog.require('goog.object');
goog.require('goog.reflect');
goog.require('goog.testing.jsunit');



/**
 * @param {number} key
 * @return {number}
 */
var doubleFn = function(key) {
  return key * 2;
};

/**
 * @param {number} key
 * @return {number}
 */
var tripleFn = function(key) {
  return key * 3;
};

/**
 * @param {number} key
 */
var throwsFn = function(key) {
  throw new Error("Shouldn't be called.");
};

/**
 * @param {string} key
 * @return {string}
 */
var passthroughFn = function(key) {
  return key;
};

function testCache() {
  var cacheObj = {};

  assertEquals(2, goog.reflect.cache(cacheObj, 1, doubleFn));
  assertEquals(2, cacheObj[1]);
  assertEquals(1, goog.object.getCount(cacheObj));

  // Ensure we get the same value with a different valueFn.
  assertEquals(2, goog.reflect.cache(cacheObj, 1, throwsFn));
  assertEquals(2, cacheObj[1]);
  assertEquals(1, goog.object.getCount(cacheObj));

  // Ensure cache works with all string keys.
  assertEquals(
      'toString', goog.reflect.cache(cacheObj, 'toString', passthroughFn));
  assertEquals('toString', goog.reflect.cache(cacheObj, 'toString', throwsFn));
  // Not checking count as it is not correct for IE8 (doesn't enumerate
  // toString).
}

function testCache_keyFn() {
  var cacheObj = {};

  assertEquals(3, goog.reflect.cache(cacheObj, 1, tripleFn, doubleFn));
  assertEquals(3, cacheObj[2]);
  assertEquals(1, goog.object.getCount(cacheObj));

  // Ensure we get the same value with a different valueFn.
  assertEquals(3, goog.reflect.cache(cacheObj, 1, throwsFn, doubleFn));
  assertEquals(3, cacheObj[2]);
  assertEquals(1, goog.object.getCount(cacheObj));

  // Ensure we set a new value if we provide a different keyFn.
  assertEquals(2, goog.reflect.cache(cacheObj, 1, doubleFn, tripleFn));
  assertEquals(2, cacheObj[3]);
  assertEquals(2, goog.object.getCount(cacheObj));

  // Ensure the keyFn is always called.
  assertThrows(function() {
    goog.reflect.cache(cacheObj, 1, tripleFn, throwsFn);
  });
}
