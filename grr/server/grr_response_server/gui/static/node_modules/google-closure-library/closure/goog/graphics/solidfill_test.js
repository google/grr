// Copyright 2012 The Closure Library Authors. All Rights Reserved.
// Use of this source code is governed by the Apache License, Version 2.0.

goog.provide('goog.graphics.SolidFillTest');
goog.setTestOnly('goog.graphics.SolidFillTest');

goog.require('goog.graphics.SolidFill');
goog.require('goog.testing.jsunit');

function testGetColor() {
  var fill = new goog.graphics.SolidFill('#123');
  assertEquals('#123', fill.getColor());
  fill = new goog.graphics.SolidFill('#abcdef');
  assertEquals('#abcdef', fill.getColor());

  fill = new goog.graphics.SolidFill('#123', 0.5);
  assertEquals('#123', fill.getColor());
  fill = new goog.graphics.SolidFill('#abcdef', 0.5);
  assertEquals('#abcdef', fill.getColor());
}

function testGetOpacity() {
  // Default opacity
  var fill = new goog.graphics.SolidFill('#123');
  assertEquals(1, fill.getOpacity());

  // Opaque
  var fill = new goog.graphics.SolidFill('#123', 1);
  assertEquals(1, fill.getOpacity());

  // Semi-transparent
  fill = new goog.graphics.SolidFill('#123', 0.5);
  assertEquals(0.5, fill.getOpacity());

  // Fully transparent
  fill = new goog.graphics.SolidFill('#123', 0);
  assertEquals(0, fill.getOpacity());
}
