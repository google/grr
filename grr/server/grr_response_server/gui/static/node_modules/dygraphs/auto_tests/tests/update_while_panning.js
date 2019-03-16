/**
 * @fileoverview Regression test for a bug involving data update while panning.
 *
 * See http://stackoverflow.com/questions/9528173
 *
 * @author dan@dygraphs.com (Dan Vanderkam)
 */
var updateWhilePanningTestCase = TestCase("update-while-panning");

updateWhilePanningTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

updateWhilePanningTestCase.prototype.tearDown = function() {
};

// This tests the following sequence:
// 1. Begin dragging a chart (x-panning)
// 2. Do a data update (updateOptions({file: ...}))
// 3. Verify that the y-axis is still well-defined.
updateWhilePanningTestCase.prototype.testUpdateWhilePanning = function() {
  var sinewave = function(start, limit, step) {
    var data = [];
    for (var x = start; x < limit; x += step) {
      data.push([x, Math.sin(x)]);
    }
    return data;
  };

  var opts = {
    width: 480,
    height: 320,
    valueRange: [-2, 2]
  };

  var graph = document.getElementById("graph");

  var g = new Dygraph(graph, sinewave(0, 6, 0.1), opts);
  assertEquals([-2, 2], g.yAxisRange());

  // Start a pan, but don't finish it yet.
  DygraphOps.dispatchMouseDown_Point(g, 200, 100, {shiftKey: true});
  DygraphOps.dispatchMouseMove_Point(g, 100, 100, {shiftKey: true});
  assertEquals([-2, 2], g.yAxisRange());

  // Now do a data update. y-axis should remain the same.
  g.updateOptions({file: sinewave(0, 7, 0.1)});
  assertEquals([-2, 2], g.yAxisRange());

  // Keep the pan going.
  DygraphOps.dispatchMouseMove_Point(g, 50, 100, {shiftKey: true});
  assertEquals([-2, 2], g.yAxisRange());

  // Now finish the pan.
  DygraphOps.dispatchMouseUp_Point(g, 100, 100, {shiftKey: true});
  assertEquals([-2, 2], g.yAxisRange());
};

