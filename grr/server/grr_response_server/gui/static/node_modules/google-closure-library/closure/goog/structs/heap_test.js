// Copyright 2006 The Closure Library Authors. All Rights Reserved.
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

goog.provide('goog.structs.HeapTest');
goog.setTestOnly('goog.structs.HeapTest');

goog.require('goog.structs');
goog.require('goog.structs.Heap');
goog.require('goog.testing.jsunit');


/**
 * Constructs a heap from key-value pairs passed as arguments
 * @param {...!Array} var_args List of length-2 arrays [key, value]
 * @return {goog.structs.Heap} Heap constructed from passed in key-value pairs
 */
function makeHeap(var_args) {
  var h = new goog.structs.Heap();
  var key, value;

  for (var i = 0; i < arguments.length; i++) {
    key = arguments[i][0];
    value = arguments[i][1];
    h.insert(key, value);
  }

  return h;
}


function testGetCount1() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  assertEquals('count, should be 4', 4, h.getCount());
  h.remove();
  assertEquals('count, should be 3', 3, h.getCount());
}

function testGetCount2() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  h.remove();
  h.remove();
  h.remove();
  h.remove();
  assertEquals('count, should be 0', 0, h.getCount());
}


function testKeys() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  var keys = h.getKeys();
  for (var i = 0; i < 4; i++) {
    assertTrue('getKeys, key ' + i + ' found', goog.structs.contains(keys, i));
  }
  assertEquals('getKeys, Should be 4 keys', 4, goog.structs.getCount(keys));
}


function testValues() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  var values = h.getValues();

  assertTrue('getKeys, value "a" found', goog.structs.contains(values, 'a'));
  assertTrue('getKeys, value "b" found', goog.structs.contains(values, 'b'));
  assertTrue('getKeys, value "c" found', goog.structs.contains(values, 'c'));
  assertTrue('getKeys, value "d" found', goog.structs.contains(values, 'd'));
  assertEquals('getKeys, Should be 4 keys', 4, goog.structs.getCount(values));
}


function testContainsKey() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);

  for (var i = 0; i < 4; i++) {
    assertTrue('containsKey, key ' + i + ' found', h.containsKey(i));
  }
  assertFalse('containsKey, value 4 not found', h.containsKey(4));
}


function testContainsValue() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);

  assertTrue('containsValue, value "a" found', h.containsValue('a'));
  assertTrue('containsValue, value "b" found', h.containsValue('b'));
  assertTrue('containsValue, value "c" found', h.containsValue('c'));
  assertTrue('containsValue, value "d" found', h.containsValue('d'));
  assertFalse('containsValue, value "e" not found', h.containsValue('e'));
}


function testClone() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  var h2 = h.clone();
  assertTrue('clone so it should not be empty', !h2.isEmpty());
  assertTrue('clone so it should contain key 0', h2.containsKey(0));
  assertTrue('clone so it should contain value "a"', h2.containsValue('a'));
}


function testClear() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  h.clear();
  assertTrue('cleared so it should be empty', h.isEmpty());
}


function testIsEmpty() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  assertFalse('4 values so should not be empty', h.isEmpty());

  h.remove();
  h.remove();
  h.remove();
  assertFalse('1 values so should not be empty', h.isEmpty());

  h.remove();
  assertTrue('0 values so should be empty', h.isEmpty());
}


function testPeek1() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  assertEquals('peek, Should be "a"', 'a', h.peek());
}


function testPeek2() {
  var h = makeHeap([1, 'b'], [3, 'd'], [0, 'a'], [2, 'c']);
  assertEquals('peek, Should be "a"', 'a', h.peek());
}


function testPeek3() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  h.clear();
  assertEquals('peek, Should be "undefined"', undefined, h.peek());
}


function testPeekKey1() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  assertEquals('peekKey, Should be "0"', 0, h.peekKey());
}


function testPeekKey2() {
  var h = makeHeap([1, 'b'], [3, 'd'], [0, 'a'], [2, 'c']);
  assertEquals('peekKey, Should be "0"', 0, h.peekKey());
}


function testPeekKey3() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);
  h.clear();
  assertEquals('peekKey, Should be "undefined"', undefined, h.peekKey());
}


function testRemove1() {
  var h = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);

  assertEquals('remove, Should be "a"', 'a', h.remove());
  assertEquals('remove, Should be "b"', 'b', h.remove());
  assertEquals('remove, Should be "c"', 'c', h.remove());
  assertEquals('remove, Should be "d"', 'd', h.remove());
}


function testRemove2() {
  var h = makeHeap([1, 'b'], [3, 'd'], [0, 'a'], [2, 'c']);

  assertEquals('remove, Should be "a"', 'a', h.remove());
  assertEquals('remove, Should be "b"', 'b', h.remove());
  assertEquals('remove, Should be "c"', 'c', h.remove());
  assertEquals('remove, Should be "d"', 'd', h.remove());
}


function testInsertPeek1() {
  var h = makeHeap();

  h.insert(3, 'd');
  assertEquals('peek, Should be "d"', 'd', h.peek());
  h.insert(2, 'c');
  assertEquals('peek, Should be "c"', 'c', h.peek());
  h.insert(1, 'b');
  assertEquals('peek, Should be "b"', 'b', h.peek());
  h.insert(0, 'a');
  assertEquals('peek, Should be "a"', 'a', h.peek());
}


function testInsertPeek2() {
  var h = makeHeap();

  h.insert(1, 'b');
  assertEquals('peek, Should be "b"', 'b', h.peek());
  h.insert(3, 'd');
  assertEquals('peek, Should be "b"', 'b', h.peek());
  h.insert(0, 'a');
  assertEquals('peek, Should be "a"', 'a', h.peek());
  h.insert(2, 'c');
  assertEquals('peek, Should be "a"', 'a', h.peek());
}

function testInsertAllPeek1() {
  var h1 = makeHeap([1, 'e']);
  var h2 = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);

  h1.insertAll(h2);
  assertEquals('peek, should be "a"', 'a', h1.peek());
}

function testInsertAllPeek2() {
  var h1 = makeHeap([-1, 'z']);
  var h2 = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);

  h1.insertAll(h2);
  assertEquals('peek, should be "z"', 'z', h1.peek());
}

function testInsertAllPeek3() {
  var h1 = makeHeap();
  var h2 = makeHeap([0, 'a'], [1, 'b'], [2, 'c'], [3, 'd']);

  h1.insertAll(h2);
  assertEquals('peek, should be "a"', 'a', h1.peek());
}
