/**
 * @license
 * Copyright 2012 Dan Vanderkam (danvdk@gmail.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */

(function() {
'use strict';

/**
 * @fileoverview Adds support for dashed lines to the HTML5 canvas.
 *
 * Usage:
 *   var ctx = canvas.getContext("2d");
 *   ctx.installPattern([10, 5])  // draw 10 pixels, skip 5 pixels, repeat.
 *   ctx.beginPath();
 *   ctx.moveTo(100, 100);  // start the first line segment.
 *   ctx.lineTo(150, 200);
 *   ctx.lineTo(200, 100);
 *   ctx.moveTo(300, 150);  // start a second, unconnected line
 *   ctx.lineTo(400, 250);
 *   ...
 *   ctx.stroke();          // draw the dashed line.
 *   ctx.uninstallPattern();
 *
 * This is designed to leave the canvas untouched when it's not used.
 * If you never install a pattern, or call uninstallPattern(), then the canvas
 * will be exactly as it would have if you'd never used this library. The only
 * difference from the standard canvas will be the "installPattern" method of
 * the drawing context.
 */

/**
 * Change the stroking style of the canvas drawing context from a solid line to
 * a pattern (e.g. dashes, dash-dot-dash, etc.)
 *
 * Once you've installed the pattern, you can draw with it by using the
 * beginPath(), moveTo(), lineTo() and stroke() method calls. Note that some
 * more advanced methods (e.g. quadraticCurveTo() and bezierCurveTo()) are not
 * supported. See file overview for a working example.
 *
 * Side effects of calling this method include adding an "isPatternInstalled"
 * property and "uninstallPattern" method to this particular canvas context.
 * You must call uninstallPattern() before calling installPattern() again.
 *
 * @param {Array.<number>} pattern A description of the stroke pattern. Even
 * indices indicate a draw and odd indices indicate a gap (in pixels). The
 * array should have a even length as any odd lengthed array could be expressed
 * as a smaller even length array.
 */
CanvasRenderingContext2D.prototype.installPattern = function(pattern) {
  if (typeof(this.isPatternInstalled) !== 'undefined') {
    throw "Must un-install old line pattern before installing a new one.";
  }
  this.isPatternInstalled = true;

  var dashedLineToHistory = [0, 0];

  // list of connected line segements:
  // [ [x1, y1], ..., [xn, yn] ], [ [x1, y1], ..., [xn, yn] ]
  var segments = [];

  // Stash away copies of the unmodified line-drawing functions.
  var realBeginPath = this.beginPath;
  var realLineTo = this.lineTo;
  var realMoveTo = this.moveTo;
  var realStroke = this.stroke;

  /** @type {function()|undefined} */
  this.uninstallPattern = function() {
    this.beginPath = realBeginPath;
    this.lineTo = realLineTo;
    this.moveTo = realMoveTo;
    this.stroke = realStroke;
    this.uninstallPattern = undefined;
    this.isPatternInstalled = undefined;
  };

  // Keep our own copies of the line segments as they're drawn.
  this.beginPath = function() {
    segments = [];
    realBeginPath.call(this);
  };
  this.moveTo = function(x, y) {
    segments.push([[x, y]]);
    realMoveTo.call(this, x, y);
  };
  this.lineTo = function(x, y) {
    var last = segments[segments.length - 1];
    last.push([x, y]);
  };

  this.stroke = function() {
    if (segments.length === 0) {
      // Maybe the user is drawing something other than a line.
      // TODO(danvk): test this case.
      realStroke.call(this);
      return;
    }

    for (var i = 0; i < segments.length; i++) {
      var seg = segments[i];
      var x1 = seg[0][0], y1 = seg[0][1];
      for (var j = 1; j < seg.length; j++) {
        // Draw a dashed line from (x1, y1) - (x2, y2)
        var x2 = seg[j][0], y2 = seg[j][1];
        this.save();

        // Calculate transformation parameters
        var dx = (x2-x1);
        var dy = (y2-y1);
        var len = Math.sqrt(dx*dx + dy*dy);
        var rot = Math.atan2(dy, dx);

        // Set transformation
        this.translate(x1, y1);
        realMoveTo.call(this, 0, 0);
        this.rotate(rot);

        // Set last pattern index we used for this pattern.
        var patternIndex = dashedLineToHistory[0];
        var x = 0;
        while (len > x) {
          // Get the length of the pattern segment we are dealing with.
          var segment = pattern[patternIndex];
          // If our last draw didn't complete the pattern segment all the way
          // we will try to finish it. Otherwise we will try to do the whole
          // segment.
          if (dashedLineToHistory[1]) {
            x += dashedLineToHistory[1];
          } else {
            x += segment;
          }

          if (x > len) {
            // We were unable to complete this pattern index all the way, keep
            // where we are the history so our next draw continues where we
            // left off in the pattern.
            dashedLineToHistory = [patternIndex, x-len];
            x = len;
          } else {
            // We completed this patternIndex, we put in the history that we
            // are on the beginning of the next segment.
            dashedLineToHistory = [(patternIndex+1)%pattern.length, 0];
          }

          // We do a line on a even pattern index and just move on a odd
          // pattern index.  The move is the empty space in the dash.
          if (patternIndex % 2 === 0) {
            realLineTo.call(this, x, 0);
          } else {
            realMoveTo.call(this, x, 0);
          }

          // If we are not done, next loop process the next pattern segment, or
          // the first segment again if we are at the end of the pattern.
          patternIndex = (patternIndex+1) % pattern.length;
        }

        this.restore();
        x1 = x2;
        y1 = y2;
      }
    }
    realStroke.call(this);
    segments = [];
  };
};

/**
 * Removes the previously-installed pattern.
 * You must call installPattern() before calling this. You can install at most
 * one pattern at a time--there is no pattern stack.
 */
CanvasRenderingContext2D.prototype.uninstallPattern = function() {
  // This will be replaced by a non-error version when a pattern is installed.
  throw "Must install a line pattern before uninstalling it.";
};

})();
