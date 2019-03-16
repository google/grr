// Copyright (c) 2011 Google, Inc.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

/** 
 * @fileoverview Assertions and other code used to test a canvas proxy.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */

var CanvasAssertions = {};

/**
 * Updates path attributes to match fill/stroke operations.
 *
 * This sets fillStyle to undefined for stroked paths,
 * and strokeStyle to undefined for filled paths, to simplify
 * matchers such as numLinesDrawn.
 *
 * @private
 * @param {Array.<Object>} List of operations.
 */
CanvasAssertions.cleanPathAttrs_ = function(calls) {
  var isStroked = true;
  for (var i = calls.length - 1; i >= 0; --i) {
    var call = calls[i];
    var name = call.name;
    if (name == 'stroke') {
      isStroked = true;
    } else if (name == 'fill') {
      isStroked = false;
    } else if (name == 'lineTo') {
      if (isStroked) {
        call.properties.fillStyle = undefined;
      } else {
        call.properties.strokeStyle = undefined;
      }
    }
  }
};


/**
 * Assert that a line is drawn between the two points
 *
 * This merely looks for one of these four possibilities:
 * moveTo(p1) -> lineTo(p2)
 * moveTo(p2) -> lineTo(p1)
 * lineTo(p1) -> lineTo(p2)
 * lineTo(p2) -> lineTo(p1)
 *
 * predicate is meant to be used when you want to track things like
 * color and stroke width. It can either be a hash of context properties,
 * or a function that accepts the current call.
 */
CanvasAssertions.assertLineDrawn = function(proxy, p1, p2, predicate) {
  CanvasAssertions.cleanPathAttrs_(proxy.calls__);
  // found = 1 when prior loop found p1.
  // found = 2 when prior loop found p2.
  var priorFound = 0;
  for (var i = 0; i < proxy.calls__.length; i++) {
    var call = proxy.calls__[i];

    // This disables lineTo -> moveTo pairs.
    if (call.name == "moveTo" && priorFound > 0) {
      priorFound = 0;
    }

    var found = 0;
    if (call.name == "moveTo" || call.name == "lineTo") {
      var matchp1 = CanvasAssertions.matchPixels(p1, call.args);
      var matchp2 = CanvasAssertions.matchPixels(p2, call.args);
      if (matchp1 || matchp2) {
        if (priorFound == 1 && matchp2) {
          if (CanvasAssertions.match(predicate, call)) {
            return;
          }
        }
        if (priorFound == 2 && matchp1) {
          if (CanvasAssertions.match(predicate, call)) {
            return;
          }
        }
        found = matchp1 ? 1 : 2;
      }
    }
    priorFound = found;
  }

  var toString = function(x) {
    var s = "{";
    for (var prop in x) {
      if (x.hasOwnProperty(prop)) {
        if (s.length > 1) {
          s = s + ", ";
        }
        s = s + prop + ": " + x[prop];
      }
    }
    return s + "}";
  };
  fail("Can't find a line drawn between " + p1 +
      " and " + p2 + " with attributes " + toString(predicate));
};

/**
 * Return the lines drawn with specific attributes.
 *
 * This merely looks for one of these four possibilities:
 * moveTo(p1) -> lineTo(p2)
 * moveTo(p2) -> lineTo(p1)
 * lineTo(p1) -> lineTo(p2)
 * lineTo(p2) -> lineTo(p1)
 *
 * attrs is meant to be used when you want to track things like
 * color and stroke width.
 */
CanvasAssertions.getLinesDrawn = function(proxy, predicate) {
  CanvasAssertions.cleanPathAttrs_(proxy.calls__);
  var lastCall;
  var lines = [];
  for (var i = 0; i < proxy.calls__.length; i++) {
    var call = proxy.calls__[i];

    if (call.name == "lineTo") {
      if (lastCall != null) {
        if (CanvasAssertions.match(predicate, call)) {
          lines.push([lastCall, call]);
        }
      }
    }

    lastCall = (call.name === "lineTo" || call.name === "moveTo") ? call : null;
  }
  return lines;
};

/**
 * Verifies that every call to context.save() has a matching call to
 * context.restore().
 */
CanvasAssertions.assertBalancedSaveRestore = function(proxy) {
  var depth = 0;
  for (var i = 0; i < proxy.calls__.length; i++) {
    var call = proxy.calls__[i];
    if (call.name == "save") depth++
    if (call.name == "restore") {
      if (depth == 0) {
        fail("Too many calls to restore()");
      }
      depth--;
    }
  }

  if (depth > 0) {
    fail("Missing matching 'context.restore()' calls.");
  }
};

/**
 * Checks how many lines of the given color have been drawn.
 * @return {Integer} The number of lines of the given color.
 */
// TODO(konigsberg): change 'color' to predicate? color is the
// common case. Possibly allow predicate to be function, hash, or
// string representing color?
CanvasAssertions.numLinesDrawn = function(proxy, color) {
  CanvasAssertions.cleanPathAttrs_(proxy.calls__);
  var num_lines = 0;
  var num_potential_calls = 0;
  for (var i = 0; i < proxy.calls__.length; i++) {
    var call = proxy.calls__[i];
    if (call.name == "beginPath") {
      num_potential_calls = 0;
    } else if (call.name == "lineTo") {
      num_potential_calls++;
    } else if (call.name == "stroke") {
      // note: Don't simplify these two conditionals into one. The
      // separation simplifies debugging tricky tests.
      if (call.properties.strokeStyle == color) {
        num_lines += num_potential_calls;
      }
      num_potential_calls = 0;
    }
  }
  return num_lines;
};

/**
 * Asserts that a series of lines are connected. For example,
 * assertConsecutiveLinesDrawn(proxy, [[x1, y1], [x2, y2], [x3, y3]], predicate)
 * is shorthand for
 * assertLineDrawn(proxy, [x1, y1], [x2, y2], predicate)
 * assertLineDrawn(proxy, [x2, y2], [x3, y3], predicate)
 */
CanvasAssertions.assertConsecutiveLinesDrawn = function(proxy, segments, predicate) {
  for (var i = 0; i < segments.length - 1; i++) {
    CanvasAssertions.assertLineDrawn(proxy, segments[i], segments[i+1], predicate);
  }
}

CanvasAssertions.matchPixels = function(expected, actual) {
  // Expect array of two integers. Assuming the values are within one
  // integer unit of each other. This should be tightened down by someone
  // who knows what pixel a value of 5.8888 results in.
  return Math.abs(expected[0] - actual[0]) < 1 &&
      Math.abs(expected[1] - actual[1]) < 1;
};

/**
 * For matching a proxy call against defined conditions.
 * predicate can either by a hash of items compared against call.properties,
 * or it can be a function that accepts the call, and returns true or false.
 * If it's null, this function returns true.
 */
CanvasAssertions.match = function(predicate, call) {
  if (predicate === null) {
    return true;
  }
  if (typeof(predicate) === "function") {
    return predicate(call);
  } else {
    for (var attr in predicate) {
      if (predicate.hasOwnProperty(attr) && predicate[attr] != call.properties[attr]) {
        return false;
      }
    }
  }
  return true;
};
