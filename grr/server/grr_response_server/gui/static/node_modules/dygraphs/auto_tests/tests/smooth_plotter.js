/**
 * @fileoverview Tests for the smooth (bezier curve) plotter.
 *
 * @author danvdk@gmail.com (Dan Vanderkam)
 */
var smoothPlotterTestCase = TestCase("smooth-plotter");

var getControlPoints = smoothPlotter._getControlPoints;

smoothPlotterTestCase.prototype.setUp = function() {
};

smoothPlotterTestCase.prototype.tearDown = function() {
};

smoothPlotterTestCase.prototype.testNoSmoothing = function() {
  var lastPt = {x: 10, y: 0},
      pt = {x: 11, y: 1},
      nextPt = {x: 12, y: 0},
      alpha = 0;

  assertEquals([11, 1, 11, 1], getControlPoints(lastPt, pt, nextPt, alpha));
};

smoothPlotterTestCase.prototype.testHalfSmoothing = function() {
  var lastPt = {x: 10, y: 0},
      pt = {x: 11, y: 1},
      nextPt = {x: 12, y: 0},
      alpha = 0.5;

  assertEquals([10.5, 1, 11.5, 1], getControlPoints(lastPt, pt, nextPt, alpha));
}

smoothPlotterTestCase.prototype.testExtrema = function() {
  var lastPt = {x: 10, y: 0},
      pt = {x: 11, y: 1},
      nextPt = {x: 12, y: 1},
      alpha = 0.5;

  assertEquals([10.5, 0.75, 11.5, 1.25],
               getControlPoints(lastPt, pt, nextPt, alpha, true));

  assertEquals([10.5, 1, 11.5, 1],
               getControlPoints(lastPt, pt, nextPt, alpha, false));
}
