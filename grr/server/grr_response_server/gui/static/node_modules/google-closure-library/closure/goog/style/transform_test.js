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

goog.provide('goog.style.transformTest');
goog.setTestOnly('goog.style.transformTest');

goog.require('goog.dom');
goog.require('goog.dom.TagName');
goog.require('goog.style');
goog.require('goog.style.transform');
goog.require('goog.testing.jsunit');
goog.require('goog.userAgent');
goog.require('goog.userAgent.product.isVersion');


/**
 * Floating point equality tolerance.
 * @const {number}
 */
var EPSILON = .0001;


/**
 * Element being transformed.
 * @type {!Element}
 */
var element;


/**
 * Sets a transform translation and asserts the translation was applied.
 * @param {number} x The horizontal translation
 * @param {number} y The vertical translation
 */
var setAndAssertTranslation = function(x, y) {
  if (goog.userAgent.GECKO ||
      goog.userAgent.IE && !goog.userAgent.isDocumentModeOrHigher(10)) {
    // Mozilla and <IE10 do not support CSSMatrix.
    return;
  }
  var success = goog.style.transform.setTranslation(element, x, y);
  if (!goog.style.transform.isSupported()) {
    assertFalse(success);
  } else {
    assertTrue(success);
    var translation = goog.style.transform.getTranslation(element);
    assertEquals(x, translation.x);
    assertEquals(y, translation.y);
  }
};


/**
 * Sets a transform translation and asserts the translation was applied.
 * @param {number} x The horizontal scale
 * @param {number} y The vertical scale
 * @param {number} z The depth scale
 */
var setAndAssertScale = function(x, y, z) {
  if (goog.userAgent.GECKO ||
      goog.userAgent.IE && !goog.userAgent.isDocumentModeOrHigher(10)) {
    // Mozilla and <IE10 do not support CSSMatrix.
    return;
  }
  var success = goog.style.transform.setScale(element, x, y, z);
  if (!goog.style.transform.isSupported()) {
    assertFalse(success);
  } else {
    assertTrue(success);
    var scale = goog.style.transform.getScale(element);
    assertEquals(x, scale.x);
    assertEquals(y, scale.y);
    if (goog.style.transform.is3dSupported()) {
      assertEquals(z, scale.z);
    }
  }
};


/**
 * Sets a transform rotation and asserts the translation was applied.
 * @param {number|function(number):boolean} expectedDegrees
 *     The expected resulting rotation in degrees, or a function to evaluate
 *     the resulting rotation.
 * @param {string=} opt_transform The plaintext CSS transform value.
 */
var setAndAssertRotation = function(expectedDegrees, opt_transform) {
  if (goog.userAgent.GECKO ||
      goog.userAgent.IE && !goog.userAgent.isDocumentModeOrHigher(10)) {
    // Mozilla and <IE10 do not support CSSMatrix.
    return;
  }
  if (opt_transform) {
    goog.style.setStyle(
        element, goog.style.transform.getTransformProperty_(), opt_transform);
  } else {
    var success =
        goog.style.transform.setRotation(element, Number(expectedDegrees));
    if (!goog.style.transform.isSupported()) {
      assertFalse(success);
      return;
    } else {
      assertTrue(success);
    }
  }
  var rotation = goog.style.transform.getRotation(element);
  if (expectedDegrees instanceof Function) {
    assertTrue('Incorrect rotation: ' + rotation, expectedDegrees(rotation));
  } else {
    assertRoughlyEquals(expectedDegrees, rotation, EPSILON);
  }
};


function setUp() {
  element = goog.dom.createElement(goog.dom.TagName.DIV);
  goog.dom.appendChild(goog.dom.getDocument().body, element);
}

function tearDown() {
  goog.dom.removeNode(element);
}


function testIsSupported() {
  if (goog.userAgent.IE && !goog.userAgent.product.isVersion(9)) {
    assertFalse(goog.style.transform.isSupported());
  } else {
    assertTrue(goog.style.transform.isSupported());
  }
}


function testIs3dSupported() {
  if (goog.userAgent.GECKO && !goog.userAgent.product.isVersion(10) ||
      (goog.userAgent.IE && !goog.userAgent.product.isVersion(10))) {
    assertFalse(goog.style.transform.is3dSupported());
  } else {
    assertTrue(goog.style.transform.is3dSupported());
  }
}

function testTranslateX() {
  setAndAssertTranslation(10, 0);
}

function testTranslateY() {
  setAndAssertTranslation(0, 10);
}

function testTranslateXY() {
  setAndAssertTranslation(10, 20);
}

function testScaleX() {
  setAndAssertScale(5, 1, 1);
}

function testScaleY() {
  setAndAssertScale(1, 3, 1);
}

function testScaleZ() {
  setAndAssertScale(1, 1, 8);
}

function testScale() {
  setAndAssertScale(2, 2, 2);
}

function testRotatePositive() {
  setAndAssertRotation(90);
}

function testRotateNegative() {
  setAndAssertRotation(-90);
}

function testGetRotationWhenScaledUp() {
  setAndAssertRotation(90, 'scale(5) rotate3d(0,0,1,90deg)');
}

function testGetRotationWhenScaledDown() {
  setAndAssertRotation(90, 'scale(.5) rotate3d(0,0,1,90deg)');
}

function testGetRotationWithSkew() {
  setAndAssertRotation(0, 'skew(30deg, 30deg)');
  // NOTE: Non-zero rotations are not well-defined with a skew, but the lower
  // and upper bounds are. So check that the rotation is within these bounds.
  setAndAssertRotation(function(x) {
    return (x > 0 && x < 30);
  }, 'skew(0, 30deg)');
  setAndAssertRotation(function(x) {
    return (x < 0 && x > -30);
  }, 'skew(30deg, 0)');
}
