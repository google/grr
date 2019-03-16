// Copyright 2012 Google Inc. All Rights Reserved.

/**
 * @fileoverview A class to facilitate sampling colors at particular pixels on a
 * dygraph.
 * @author danvk@google.com (Dan Vanderkam)
 */

'use strict';

/**
 * @constructor
 */
var PixelSampler = function(dygraph) {
  this.dygraph_ = dygraph;

  var canvas = dygraph.hidden_;
  var ctx = canvas.getContext("2d");
  this.imageData_ = ctx.getImageData(0, 0, canvas.width, canvas.height);
  this.scale = canvas.width / dygraph.width_;
};

/**
 * @param {number} x The screen x-coordinate at which to sample.
 * @param {number} y The screen y-coordinate at which to sample.
 * @return {Array.<number>} a 4D array: [R, G, B, alpha]. All four values
 * are in [0, 255]. A pixel which has never been touched will be [0,0,0,0].
 */
PixelSampler.prototype.colorAtPixel = function(x, y) {
  var i = 4 * (x * this.scale + this.imageData_.width * y * this.scale);
  var d = this.imageData_.data;
  return [d[i], d[i+1], d[i+2], d[i+3]];
};

/**
 * The method samples a color using data coordinates (not screen coordinates).
 * This will round your data coordinates to the nearest screen pixel before
 * sampling.
 * @param {number} x The data x-coordinate at which to sample.
 * @param {number} y The data y-coordinate at which to sample.
 * @return {Array.<number>} a 4D array: [R, G, B, alpha]. All four values
 * are in [0, 255]. A pixel which has never been touched will be [0,0,0,0].
 */
PixelSampler.prototype.colorAtCoordinate = function(x, y) {
  var dom_xy = this.dygraph_.toDomCoords(x, y);
  return this.colorAtPixel(Math.round(dom_xy[0]), Math.round(dom_xy[1]));
};
