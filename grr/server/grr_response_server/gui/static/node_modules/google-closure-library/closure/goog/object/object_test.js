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

goog.provide('goog.objectTest');
goog.setTestOnly('goog.objectTest');

goog.require('goog.array');
goog.require('goog.functions');
goog.require('goog.object');
goog.require('goog.testing.jsunit');
goog.require('goog.testing.recordFunction');

function stringifyObject(m) {
  var keys = goog.object.getKeys(m);
  var s = '';
  for (var i = 0; i < keys.length; i++) {
    s += keys[i] + goog.object.get(m, keys[i]);
  }
  return s;
}

function getObject() {
  return {a: 0, b: 1, c: 2, d: 3};
}

function testKeys() {
  var m = getObject();
  assertEquals(
      'getKeys, The keys should be a,b,c', 'a,b,c,d',
      goog.object.getKeys(m).join(','));
}

function testValues() {
  var m = getObject();
  assertEquals(
      'getValues, The values should be 0,1,2', '0,1,2,3',
      goog.object.getValues(m).join(','));
}

function testGetAnyKey() {
  var m = getObject();
  assertTrue(
      'getAnyKey, The key should be a,b,c or d', goog.object.getAnyKey(m) in m);
  assertUndefined(
      'getAnyKey, The key should be undefined', goog.object.getAnyKey({}));
}

function testGetAnyValue() {
  var m = getObject();
  assertTrue(
      'getAnyValue, The value should be 0,1,2 or 3',
      goog.object.containsValue(m, goog.object.getAnyValue(m)));
  assertUndefined(
      'getAnyValue, The value should be undefined',
      goog.object.getAnyValue({}));
}

function testContainsKey() {
  var m = getObject();
  assertTrue(
      "containsKey, Should contain the 'a' key",
      goog.object.containsKey(m, 'a'));
  assertFalse(
      "containsKey, Should not contain the 'e' key",
      goog.object.containsKey(m, 'e'));
}

function testContainsValue() {
  var m = getObject();
  assertTrue(
      'containsValue, Should contain the value 0',
      goog.object.containsValue(m, 0));
  assertFalse(
      'containsValue, Should not contain the value 4',
      goog.object.containsValue(m, 4));
  assertTrue('isEmpty, The map should not be empty', !goog.object.isEmpty(m));
}

function testFindKey() {
  var dict = {'a': 1, 'b': 2, 'c': 3, 'd': 4};
  var key = goog.object.findKey(dict, function(v, k, d) {
    assertEquals('valid 3rd argument', dict, d);
    assertTrue('valid 1st argument', goog.object.containsValue(d, v));
    assertTrue('valid 2nd argument', k in d);
    return v % 3 == 0;
  });
  assertEquals('key "c" found', 'c', key);

  var pred = function(value) { return value > 5; };
  assertUndefined('no match', goog.object.findKey(dict, pred));
}

function testFindValue() {
  var dict = {'a': 1, 'b': 2, 'c': 3, 'd': 4};
  var value = goog.object.findValue(dict, function(v, k, d) {
    assertEquals('valid 3rd argument', dict, d);
    assertTrue('valid 1st argument', goog.object.containsValue(d, v));
    assertTrue('valid 2nd argument', k in d);
    return k.toUpperCase() == 'C';
  });
  assertEquals('value 3 found', 3, value);

  var pred = function(value, key) { return key > 'd'; };
  assertUndefined('no match', goog.object.findValue(dict, pred));
}

function testClear() {
  var m = getObject();
  goog.object.clear(m);
  assertTrue('cleared so it should be empty', goog.object.isEmpty(m));
  assertFalse(
      "cleared so it should not contain 'a' key",
      goog.object.containsKey(m, 'a'));
}

function testClone() {
  var m = getObject();
  var m2 = goog.object.clone(m);
  assertFalse('clone so it should not be empty', goog.object.isEmpty(m2));
  assertTrue(
      "clone so it should contain 'c' key", goog.object.containsKey(m2, 'c'));
}

function testUnsafeClonePrimitive() {
  assertEquals(
      'cloning a primitive should return an equal primitive', 5,
      goog.object.unsafeClone(5));
}

function testUnsafeCloneObjectThatHasACloneMethod() {
  var original = {
    name: 'original',
    clone: goog.functions.constant({name: 'clone'})
  };

  var clone = goog.object.unsafeClone(original);
  assertEquals('original', original.name);
  assertEquals('clone', clone.name);
}

function testUnsafeCloneObjectThatHasACloneNonMethod() {
  var originalIndex = {red: [0, 4], clone: [1, 3, 5, 7], yellow: [2, 6]};

  var clone = goog.object.unsafeClone(originalIndex);
  assertArrayEquals([1, 3, 5, 7], originalIndex.clone);
  assertArrayEquals([1, 3, 5, 7], clone.clone);
}

function testUnsafeCloneFlatObject() {
  var original = {a: 1, b: 2, c: 3};
  var clone = goog.object.unsafeClone(original);
  assertNotEquals(original, clone);
  assertObjectEquals(original, clone);
}

function testUnsafeCloneDeepObject() {
  var original = {a: 1, b: {c: 2, d: 3}, e: {f: {g: 4, h: 5}}};
  var clone = goog.object.unsafeClone(original);

  assertNotEquals(original, clone);
  assertNotEquals(original.b, clone.b);
  assertNotEquals(original.e, clone.e);

  assertEquals(1, clone.a);
  assertEquals(2, clone.b.c);
  assertEquals(3, clone.b.d);
  assertEquals(4, clone.e.f.g);
  assertEquals(5, clone.e.f.h);
}

function testUnsafeCloneFunctions() {
  var original = {f: goog.functions.constant('hi')};
  var clone = goog.object.unsafeClone(original);

  assertNotEquals(original, clone);
  assertEquals('hi', clone.f());
  assertEquals(original.f, clone.f);
}

function testForEach() {
  var m = getObject();
  var s = '';
  goog.object.forEach(m, function(val, key, m2) {
    assertNotUndefined(key);
    assertEquals(m, m2);
    s += key + val;
  });
  assertEquals(s, 'a0b1c2d3');
}

function testFilter() {
  var m = getObject();

  var m2 = goog.object.filter(m, function(val, key, m3) {
    assertNotUndefined(key);
    assertEquals(m, m3);
    return val > 1;
  });
  assertEquals(stringifyObject(m2), 'c2d3');
}


function testMap() {
  var m = getObject();
  var m2 = goog.object.map(m, function(val, key, m3) {
    assertNotUndefined(key);
    assertEquals(m, m3);
    return val * val;
  });
  assertEquals(stringifyObject(m2), 'a0b1c4d9');
}

function testSome() {
  var m = getObject();
  var b = goog.object.some(m, function(val, key, m2) {
    assertNotUndefined(key);
    assertEquals(m, m2);
    return val > 1;
  });
  assertTrue(b);
  var b = goog.object.some(m, function(val, key, m2) {
    assertNotUndefined(key);
    assertEquals(m, m2);
    return val > 100;
  });
  assertFalse(b);
}

function testEvery() {
  var m = getObject();
  var b = goog.object.every(m, function(val, key, m2) {
    assertNotUndefined(key);
    assertEquals(m, m2);
    return val >= 0;
  });
  assertTrue(b);
  b = goog.object.every(m, function(val, key, m2) {
    assertNotUndefined(key);
    assertEquals(m, m2);
    return val > 1;
  });
  assertFalse(b);
}

function testContains() {
  var m = getObject();
  assertTrue(goog.object.contains(m, 3));
  assertFalse(goog.object.contains(m, 4));
}

function testObjectProperties() {
  var m = {};

  goog.object.set(m, 'toString', 'once');
  goog.object.set(m, 'valueOf', 'upon');
  goog.object.set(m, 'eval', 'a');
  goog.object.set(m, 'toSource', 'midnight');
  goog.object.set(m, 'prototype', 'dreary');
  goog.object.set(m, 'hasOwnProperty', 'dark');

  assertEquals(goog.object.get(m, 'toString'), 'once');
  assertEquals(goog.object.get(m, 'valueOf'), 'upon');
  assertEquals(goog.object.get(m, 'eval'), 'a');
  assertEquals(goog.object.get(m, 'toSource'), 'midnight');
  assertEquals(goog.object.get(m, 'prototype'), 'dreary');
  assertEquals(goog.object.get(m, 'hasOwnProperty'), 'dark');
}

function testSetDefault() {
  var dict = {};
  assertEquals(1, goog.object.setIfUndefined(dict, 'a', 1));
  assertEquals(1, dict['a']);
  assertEquals(1, goog.object.setIfUndefined(dict, 'a', 2));
  assertEquals(1, dict['a']);
}

function createRecordedGetFoo() {
  return goog.testing.recordFunction(goog.functions.constant('foo'));
}

function testSetWithReturnValueNotSet_KeyIsSet() {
  var f = createRecordedGetFoo();
  var obj = {};
  obj['key'] = 'bar';
  assertEquals('bar', goog.object.setWithReturnValueIfNotSet(obj, 'key', f));
  f.assertCallCount(0);
}

function testSetWithReturnValueNotSet_KeyIsNotSet() {
  var f = createRecordedGetFoo();
  var obj = {};
  assertEquals('foo', goog.object.setWithReturnValueIfNotSet(obj, 'key', f));
  f.assertCallCount(1);
}

function testSetWithReturnValueNotSet_KeySetValueIsUndefined() {
  var f = createRecordedGetFoo();
  var obj = {};
  obj['key'] = undefined;
  assertEquals(
      undefined, goog.object.setWithReturnValueIfNotSet(obj, 'key', f));
  f.assertCallCount(0);
}

function testTranspose() {
  var m = getObject();
  var b = goog.object.transpose(m);
  assertEquals('a', b[0]);
  assertEquals('b', b[1]);
  assertEquals('c', b[2]);
  assertEquals('d', b[3]);
}

function testExtend() {
  var o = {};
  var o2 = {a: 0, b: 1};
  goog.object.extend(o, o2);
  assertEquals(0, o.a);
  assertEquals(1, o.b);
  assertTrue('a' in o);
  assertTrue('b' in o);

  o2 = {c: 2};
  goog.object.extend(o, o2);
  assertEquals(2, o.c);
  assertTrue('c' in o);

  o2 = {c: 3};
  goog.object.extend(o, o2);
  assertEquals(3, o.c);
  assertTrue('c' in o);

  o = {};
  o2 = {c: 2};
  var o3 = {c: 3};
  goog.object.extend(o, o2, o3);
  assertEquals(3, o.c);
  assertTrue('c' in o);

  o = {};
  o2 = {a: 0, b: 1};
  o3 = {c: 2, d: 3};
  goog.object.extend(o, o2, o3);
  assertEquals(0, o.a);
  assertEquals(1, o.b);
  assertEquals(2, o.c);
  assertEquals(3, o.d);
  assertTrue('a' in o);
  assertTrue('b' in o);
  assertTrue('c' in o);
  assertTrue('d' in o);

  o = {};
  o2 = {
    'constructor': 0,
    'hasOwnProperty': 1,
    'isPrototypeOf': 2,
    'propertyIsEnumerable': 3,
    'toLocaleString': 4,
    'toString': 5,
    'valueOf': 6
  };
  goog.object.extend(o, o2);
  assertEquals(0, o['constructor']);
  assertEquals(1, o['hasOwnProperty']);
  assertEquals(2, o['isPrototypeOf']);
  assertEquals(3, o['propertyIsEnumerable']);
  assertEquals(4, o['toLocaleString']);
  assertEquals(5, o['toString']);
  assertEquals(6, o['valueOf']);
  assertTrue('constructor' in o);
  assertTrue('hasOwnProperty' in o);
  assertTrue('isPrototypeOf' in o);
  assertTrue('propertyIsEnumerable' in o);
  assertTrue('toLocaleString' in o);
  assertTrue('toString' in o);
  assertTrue('valueOf' in o);
}

function testCreate() {
  assertObjectEquals(
      'With multiple arguments', {a: 0, b: 1},
      goog.object.create('a', 0, 'b', 1));
  assertObjectEquals(
      'With an array argument', {a: 0, b: 1},
      goog.object.create(['a', 0, 'b', 1]));

  assertObjectEquals('With no arguments', {}, goog.object.create());
  assertObjectEquals(
      'With an ampty array argument', {}, goog.object.create([]));

  assertThrows('Should throw due to uneven arguments', function() {
    goog.object.create('a');
  });
  assertThrows('Should throw due to uneven arguments', function() {
    goog.object.create('a', 0, 'b');
  });
  assertThrows('Should throw due to uneven length array', function() {
    goog.object.create(['a']);
  });
  assertThrows('Should throw due to uneven length array', function() {
    goog.object.create(['a', 0, 'b']);
  });
}

function testCreateSet() {
  assertObjectEquals(
      'With multiple arguments', {a: true, b: true},
      goog.object.createSet('a', 'b'));
  assertObjectEquals(
      'With an array argument', {a: true, b: true},
      goog.object.createSet(['a', 'b']));

  assertObjectEquals('With no arguments', {}, goog.object.createSet());
  assertObjectEquals(
      'With an ampty array argument', {}, goog.object.createSet([]));
}

function createTestDeepObject() {
  var obj = {};
  obj.a = {};
  obj.a.b = {};
  obj.a.b.c = {};
  obj.a.b.c.fooArr = [5, 6, 7, 8];
  obj.a.b.c.knownNull = null;
  obj.knownEmptyString = '';
  obj.knownSingleCharacterString = '1';

  return obj;
}

function testGetValueByKeys() {
  var obj = createTestDeepObject();
  assertEquals(obj, goog.object.getValueByKeys(obj));
  assertEquals(obj.a, goog.object.getValueByKeys(obj, 'a'));
  assertEquals(obj.a.b, goog.object.getValueByKeys(obj, 'a', 'b'));
  assertEquals(obj.a.b.c, goog.object.getValueByKeys(obj, 'a', 'b', 'c'));
  assertEquals(
      obj.a.b.c.d, goog.object.getValueByKeys(obj, 'a', 'b', 'c', 'd'));
  assertEquals(8, goog.object.getValueByKeys(obj, 'a', 'b', 'c', 'fooArr', 3));
  assertNull(goog.object.getValueByKeys(obj, 'a', 'b', 'c', 'knownNull'));
  assertUndefined(
      goog.object.getValueByKeys(obj, 'a', 'b', 'c', 'knownNull', 'd'));
  assertUndefined(goog.object.getValueByKeys(obj, 'e', 'f', 'g'));
  assertEquals(
      0, goog.object.getValueByKeys(obj, 'knownEmptyString', 'length'));
  assertEquals(
      1,
      goog.object.getValueByKeys(obj, 'knownSingleCharacterString', 'length'));
}

function testGetValueByKeysArraySyntax() {
  var obj = createTestDeepObject();
  assertEquals(obj, goog.object.getValueByKeys(obj, []));
  assertEquals(obj.a, goog.object.getValueByKeys(obj, ['a']));

  assertEquals(obj.a.b, goog.object.getValueByKeys(obj, ['a', 'b']));
  assertEquals(obj.a.b.c, goog.object.getValueByKeys(obj, ['a', 'b', 'c']));
  assertEquals(
      obj.a.b.c.d, goog.object.getValueByKeys(obj, ['a', 'b', 'c', 'd']));
  assertEquals(
      8, goog.object.getValueByKeys(obj, ['a', 'b', 'c', 'fooArr', 3]));
  assertNull(goog.object.getValueByKeys(obj, ['a', 'b', 'c', 'knownNull']));
  assertUndefined(
      goog.object.getValueByKeys(obj, ['a', 'b', 'c', 'knownNull', 'd']));
  assertUndefined(goog.object.getValueByKeys(obj, 'e', 'f', 'g'));
}

function testImmutableView() {
  if (!Object.isFrozen) {
    return;
  }
  var x = {propA: 3};
  var y = goog.object.createImmutableView(x);
  x.propA = 4;
  x.propB = 6;
  y.propA = 5;
  y.propB = 7;
  assertEquals(4, x.propA);
  assertEquals(6, x.propB);
  assertFalse(goog.object.isImmutableView(x));

  assertEquals(4, y.propA);
  assertEquals(6, y.propB);
  assertTrue(goog.object.isImmutableView(y));

  assertFalse('x and y should be different references', x == y);
  assertTrue(
      'createImmutableView should not create a new view of an immutable object',
      y == goog.object.createImmutableView(y));
}

function testImmutableViewStrict() {
  'use strict';

  // IE9 supports isFrozen, but does not support strict mode. Exit early if we
  // are not actually running in strict mode.
  var isStrict = (function() { return !this; })();

  if (!Object.isFrozen || !isStrict) {
    return;
  }
  var x = {propA: 3};
  var y = goog.object.createImmutableView(x);
  assertThrows(function() { y.propA = 4; });
  assertThrows(function() { y.propB = 4; });
}

function testEmptyObjectsAreEqual() {
  assertTrue(goog.object.equals({}, {}));
}

function testObjectsWithDifferentKeysAreUnequal() {
  assertFalse(goog.object.equals({'a': 1}, {'b': 1}));
}

function testObjectsWithDifferentValuesAreUnequal() {
  assertFalse(goog.object.equals({'a': 1}, {'a': 2}));
}

function testObjectsWithSameKeysAndValuesAreEqual() {
  assertTrue(goog.object.equals({'a': 1}, {'a': 1}));
}

function testObjectsWithSameKeysInDifferentOrderAreEqual() {
  assertTrue(goog.object.equals({'a': 1, 'b': 2}, {'b': 2, 'a': 1}));
}

function testIs() {
  var object = {};
  assertTrue(goog.object.is(object, object));
  assertFalse(goog.object.is(object, {}));

  assertTrue(goog.object.is(NaN, NaN));
  assertTrue(goog.object.is(0, 0));
  assertTrue(goog.object.is(1, 1));
  assertTrue(goog.object.is(-1, -1));
  assertTrue(goog.object.is(123, 123));
  assertFalse(goog.object.is(0, -0));
  assertFalse(goog.object.is(-0, 0));
  assertFalse(goog.object.is(0, 1));

  assertTrue(goog.object.is(true, true));
  assertTrue(goog.object.is(false, false));
  assertFalse(goog.object.is(true, false));
  assertFalse(goog.object.is(false, true));

  assertTrue(goog.object.is('', ''));
  assertTrue(goog.object.is('a', 'a'));
  assertFalse(goog.object.is('', 'a'));
  assertFalse(goog.object.is('a', ''));
  assertFalse(goog.object.is('a', 'b'));

  assertFalse(goog.object.is(true, 'true'));
  assertFalse(goog.object.is('true', true));
  assertFalse(goog.object.is(false, 'false'));
  assertFalse(goog.object.is('false', false));
  assertFalse(goog.object.is(0, '0'));
  assertFalse(goog.object.is('0', 0));
}

function testGetAllPropertyNames_enumerableProperties() {
  var obj = {a: function() {}, b: 'b', c: function(x) {}};
  assertSameElements(['a', 'b', 'c'], goog.object.getAllPropertyNames(obj));
}

function testGetAllPropertyNames_nonEnumerableProperties() {
  var obj = {};
  try {
    Object.defineProperty(obj, 'foo', {value: 'bar', enumerable: false});
  } catch (ex) {
    // IE8 doesn't allow Object.defineProperty on non-DOM elements.
    if (ex.message == 'Object doesn\'t support this action') {
      return;
    }
  }

  var expected = goog.isDef(Object.getOwnPropertyNames) ? ['foo'] : [];
  assertSameElements(expected, goog.object.getAllPropertyNames(obj));
}

function testGetAllPropertyNames_inheritedProperties() {
  var parent = function() {};
  parent.prototype.a = null;

  var child = function() {};
  goog.inherits(child, parent);
  child.prototype.b = null;

  var expected = ['a', 'b'];
  if (goog.isDef(Object.getOwnPropertyNames)) {
    expected.push('constructor');
  }

  assertSameElements(
      expected, goog.object.getAllPropertyNames(child.prototype));
}

function testGetAllPropertyNames_es6ClassProperties() {
  // Create an ES6 class via eval so we can bail out if it's a syntax error in
  // browsers that don't support ES6 classes.
  try {
    eval(
        'var Foo = class {' +
        '  a() {}' +
        '};' +
        'Foo.prototype.b = null;' +
        'var Bar = class extends Foo {' +
        '  c() {}' +
        '  static d() {}' +
        '};');
  } catch (e) {
    if (e instanceof SyntaxError) {
      return;
    }
  }

  assertSameElements(
      ['a', 'b', 'constructor'],
      goog.object.getAllPropertyNames(Foo.prototype));
  assertSameElements(
      ['a', 'b', 'c', 'constructor'],
      goog.object.getAllPropertyNames(Bar.prototype));

  var expectedBarProperties = ['d', 'prototype', 'length', 'name'];

  // Some versions of Firefox don't find the name property via
  // getOwnPropertyNames.
  if (!goog.array.contains(Object.getOwnPropertyNames(Bar), 'name')) {
    goog.array.remove(expectedBarProperties, 'name');
  }

  assertSameElements(
      expectedBarProperties, goog.object.getAllPropertyNames(Bar));
}

function testGetAllPropertyNames_includeObjectPrototype() {
  var obj = {a: function() {}, b: 'b', c: function(x) {}};

  // There's slightly different behavior depending on what APIs the browser
  // under test supports.
  var additionalProps = !!Object.getOwnPropertyNames ?
      Object.getOwnPropertyNames(Object.prototype) :
      [];
  // __proto__ is a bit special and should be excluded from the result set.
  goog.array.remove(additionalProps, '__proto__');

  assertSameElements(
      ['a', 'b', 'c'].concat(additionalProps),
      goog.object.getAllPropertyNames(obj, true));
}

function testGetAllPropertyNames_includeFunctionPrototype() {
  var obj = function() {};
  obj.a = function() {};

  // There's slightly different behavior depending on what APIs the browser
  // under test supports.
  var additionalProps = !!Object.getOwnPropertyNames ?
      Object.getOwnPropertyNames(Function.prototype).concat(['prototype']) :
      [];

  var expectedElements = ['a'].concat(additionalProps);
  goog.array.removeDuplicates(expectedElements);

  assertSameElements(
      expectedElements, goog.object.getAllPropertyNames(obj, false, true));
}
