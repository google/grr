/** 
 * @fileoverview Tests for stand-alone functions in dygraph-utils.js
 *
 * @author danvdk@gmail.com (Dan Vanderkam)
 */

var UtilsTestCase = TestCase("utils-tests");

UtilsTestCase.prototype.testUpdate = function() {
  var a = {
    a: 1,
    b: [1, 2, 3],
    c: { x: 1, y: 2},
    d: { f: 10, g: 20}
  };
  assertEquals(1, a['a']);
  assertEquals([1, 2, 3], a['b']);
  assertEquals({x: 1, y: 2}, a['c']);
  assertEquals({f: 10, g: 20}, a['d']);

  Dygraph.update(a, { c: { x: 2 } });
  assertEquals({x: 2}, a['c']);

  Dygraph.update(a, { d: null });
  assertEquals(null, a['d']);

  Dygraph.update(a, { a: 10, b: [1, 2] });
  assertEquals(10, a['a']);
  assertEquals([1, 2], a['b']);
  assertEquals({x: 2}, a['c']);
  assertEquals(null, a['d']);
};

UtilsTestCase.prototype.testUpdateDeep = function() {
  var a = {
    a: 1,
    b: [1, 2, 3],
    c: { x: 1, y: 2},
    d: { f: 10, g: 20}
  };
  assertEquals(1, a['a']);
  assertEquals([1, 2, 3], a['b']);
  assertEquals({x: 1, y: 2}, a['c']);
  assertEquals({f: 10, g: 20}, a['d']);

  Dygraph.updateDeep(a, { c: { x: 2 } });
  assertEquals({x: 2, y: 2}, a['c']);

  Dygraph.updateDeep(a, { d: null });
  assertEquals(null, a['d']);

  Dygraph.updateDeep(a, { a: 10, b: [1, 2] });
  assertEquals(10, a['a']);
  assertEquals([1, 2], a['b']);
  assertEquals({x: 2, y: 2}, a['c']);
  assertEquals(null, a['d']);
};

UtilsTestCase.prototype.testUpdateDeepDecoupled = function() {
  var a = {
    a: 1,
    b: [1, 2, 3],
    c: { x: "original", y: 2},
  };

  var b = {};
  Dygraph.updateDeep(b, a);

  b.a = 2;
  assertEquals(1, a.a);

  b.b[0] = 2;
  assertEquals(1, a.b[0]);

  b.c.x = "new value";
  assertEquals("original", a.c.x);
};


UtilsTestCase.prototype.testIterator_nopredicate = function() {
  var array = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  var iter = Dygraph.createIterator(array, 1, 4);
  assertTrue(iter.hasNext);
  assertEquals('b', iter.peek);
  assertEquals('b', iter.next());
  assertTrue(iter.hasNext);

  assertEquals('c', iter.peek);
  assertEquals('c', iter.next());

  assertTrue(iter.hasNext);
  assertEquals('d', iter.next());

  assertTrue(iter.hasNext);
  assertEquals('e', iter.next());

  assertFalse(iter.hasNext);
};

UtilsTestCase.prototype.testIterator_predicate = function() {
  var array = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  var iter = Dygraph.createIterator(array, 1, 4,
      function(array, idx) { return array[idx] !== 'd' });
  assertTrue(iter.hasNext);
  assertEquals('b', iter.peek);
  assertEquals('b', iter.next());
  assertTrue(iter.hasNext);

  assertEquals('c', iter.peek);
  assertEquals('c', iter.next());

  assertTrue(iter.hasNext);
  assertEquals('e', iter.next());

  assertFalse(iter.hasNext);
}

UtilsTestCase.prototype.testIterator_empty = function() {
  var array = [];
  var iter = Dygraph.createIterator([], 0, 0);
  assertFalse(iter.hasNext);
};

UtilsTestCase.prototype.testIterator_outOfRange = function() {
  var array = ['a', 'b', 'c'];
  var iter = Dygraph.createIterator(array, 1, 4,
      function(array, idx) { return array[idx] !== 'd' });
  assertTrue(iter.hasNext);
  assertEquals('b', iter.peek);
  assertEquals('b', iter.next());
  assertTrue(iter.hasNext);

  assertEquals('c', iter.peek);
  assertEquals('c', iter.next());

  assertFalse(iter.hasNext);
};

// Makes sure full array is tested, and that the predicate isn't called
// with invalid boundaries.
UtilsTestCase.prototype.testIterator_whole_array = function() {
  var array = ['a', 'b', 'c'];
  var iter = Dygraph.createIterator(array, 0, array.length,
      function(array, idx) {
        if (idx < 0 || idx >= array.length) {
          throw "err";
        } else {
          return true;
        };
      });
  assertTrue(iter.hasNext);
  assertEquals('a', iter.next());
  assertTrue(iter.hasNext);
  assertEquals('b', iter.next());
  assertTrue(iter.hasNext);
  assertEquals('c', iter.next());
  assertFalse(iter.hasNext);
  assertNull(iter.next());
};

UtilsTestCase.prototype.testIterator_no_args = function() {
  var array = ['a', 'b', 'c'];
  var iter = Dygraph.createIterator(array);
  assertTrue(iter.hasNext);
  assertEquals('a', iter.next());
  assertTrue(iter.hasNext);
  assertEquals('b', iter.next());
  assertTrue(iter.hasNext);
  assertEquals('c', iter.next());
  assertFalse(iter.hasNext);
  assertNull(iter.next());
};

UtilsTestCase.prototype.testToRGB = function() {
  assertEquals({r: 255, g: 200, b: 150}, Dygraph.toRGB_('rgb(255,200,150)'));
  assertEquals({r: 255, g: 200, b: 150}, Dygraph.toRGB_('#FFC896'));
  assertEquals({r: 255, g: 0, b: 0}, Dygraph.toRGB_('red'));
  assertEquals({r: 255, g: 200, b: 150, a: 0.6},
                   Dygraph.toRGB_('rgba(255, 200, 150, 0.6)'));
};

UtilsTestCase.prototype.testIsPixelChangingOptionList = function() {
  var isPx = Dygraph.isPixelChangingOptionList;
  assertTrue(isPx([], { axes: { y: { digitsAfterDecimal: 3 }}}));
  assertFalse(isPx([], { axes: { y: { axisLineColor: 'blue' }}}));
};

/*
UtilsTestCase.prototype.testDateSet = function() {
  var base = new Date(1383455100000);
  var d = new Date(base);

  // A one hour shift -- this is surprising behavior!
  d.setMilliseconds(10);
  assertEquals(3600010, d.getTime() - base.getTime());

  // setDateSameTZ compensates for this surprise.
  d = new Date(base);
  Dygraph.setDateSameTZ(d, {ms: 10});
  assertEquals(10, d.getTime() - base.getTime());
};
*/
