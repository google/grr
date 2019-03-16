/**
 * @fileoverview FILL THIS IN
 *
 * @author danvk@google.com (Dan Vanderkam)
 */
var errorBarsTestCase = TestCase("error-bars");

errorBarsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

errorBarsTestCase._origFunc = Dygraph.getContext;
errorBarsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
  Dygraph.getContext = function(canvas) {
    return new Proxy(errorBarsTestCase._origFunc(canvas));
  }
};

errorBarsTestCase.prototype.tearDown = function() {
  Dygraph.getContext = errorBarsTestCase._origFunc;
};

errorBarsTestCase.prototype.testErrorBarsDrawn = function() {
  var opts = {
    width: 480,
    height: 320,
    drawXGrid: false,
    drawYGrid: false,
    drawXAxis: false,
    drawYAxis: false,
    customBars: true,
    errorBars: true
  };
  var data = [
               [1, [10,  10, 100]],
               [2, [15,  20, 110]],
               [3, [10,  30, 100]],
               [4, [15,  40, 110]],
               [5, [10, 120, 100]],
               [6, [15,  50, 110]],
               [7, [10,  70, 100]],
               [8, [15,  90, 110]],
               [9, [10,  50, 100]]
             ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  htx = g.hidden_ctx_;

  var attrs = {};  // TODO(danvk): fill in

  for (var i = 0; i < data.length - 1; i++) {
    // bottom line
    var xy1 = g.toDomCoords(data[i][0], data[i][1][0]);
    var xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][1][0]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // top line
    xy1 = g.toDomCoords(data[i][0], data[i][1][2]);
    xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][1][2]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // middle line
    xy1 = g.toDomCoords(data[i][0], data[i][1][1]);
    xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][1][1]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  }

  g.updateOptions({logscale: true});

  for (var i = 0; i < data.length - 1; i++) {
    // bottom line
    var xy1 = g.toDomCoords(data[i][0], data[i][1][0]);
    var xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][1][0]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // top line
    xy1 = g.toDomCoords(data[i][0], data[i][1][2]);
    xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][1][2]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // middle line
    xy1 = g.toDomCoords(data[i][0], data[i][1][1]);
    xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][1][1]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  }
  g.destroy(); // Restore balanced saves and restores.
  CanvasAssertions.assertBalancedSaveRestore(htx);
};

errorBarsTestCase.prototype.testErrorBarsCorrectColors = function() {
  // Two constant series with constant error.
  var data = [
    [0, [100, 50], [200, 50]],
    [1, [100, 50], [200, 50]]
  ];

  var opts = {
    errorBars: true,
    sigma: 1.0,
    fillAlpha: 0.15,
    colors: ['#00ff00', '#0000ff'],
    drawXGrid: false,
    drawYGrid: false,
    drawXAxis: false,
    drawYAxis: false,
    width: 400,
    height: 300,
    valueRange: [0, 300],
    labels: ['X', 'Y1', 'Y2']
  };
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  // y-pixels (0=top, 299=bottom)
  //   0- 48: empty (white)
  //  49- 98: Y2 error bar
  //  99:     Y2 center line
  // 100-148: Y2 error bar
  // 149-198: Y1 error bar
  // 199:     Y1 center line
  // 200-248: Y1 error bar
  // 249-299: empty (white)
  // TODO(danvk): test the edges of these regions.

  assertEquals([0, 0, 255, 38], Util.samplePixel(g.hidden_, 200, 75));
  assertEquals([0, 0, 255, 38], Util.samplePixel(g.hidden_, 200, 125));
  assertEquals([0, 255, 0, 38], Util.samplePixel(g.hidden_, 200, 175));
  assertEquals([0, 255, 0, 38], Util.samplePixel(g.hidden_, 200, 225));
};

/*

// Regression test for https://github.com/danvk/dygraphs/issues/517
// This verifies that the error bars have alpha=fillAlpha, even if the series
// color has its own alpha value.
it('testErrorBarsForAlphaSeriesCorrectColors', function() {
  var data = [
    [0, [100, 50]],
    [2, [100, 50]]
  ];

  var opts = {
    errorBars: true,
    sigma: 1.0,
    fillAlpha: 0.15,
    strokeWidth: 10,
    colors: ['rgba(0, 255, 0, 0.5)'],
    axes : {
      x : {
        drawGrid: false,
        drawAxis: false,
      },
      y : {
        drawGrid: false,
        drawAxis: false,
      }
    },
    width: 400,
    height: 300,
    valueRange: [0, 300],
    labels: ['X', 'Y']
  };
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  // y-pixels (0=top, 299=bottom)
  //   0-148: empty (white)
  // 149-198: Y error bar
  // 199:     Y center line
  // 200-248: Y error bar
  // 249-299: empty (white)

  //  38 = 255 * 0.15 (fillAlpha)
  // 146 = 255 * (0.15 * 0.5 + 1 * 0.5) (fillAlpha from error bar + alpha from series line)
  assert.deepEqual([0, 255, 0, 38],  Util.samplePixel(g.hidden_, 1, 175));
  assert.deepEqual([0, 255, 0, 146], Util.samplePixel(g.hidden_, 200, 199));
  assert.deepEqual([0, 255, 0, 38],  Util.samplePixel(g.hidden_, 1, 225));
});

*/


// Regression test for http://code.google.com/p/dygraphs/issues/detail?id=392
errorBarsTestCase.prototype.testRollingAveragePreservesNaNs = function() {
  var graph = document.getElementById("graph");
  var data = 
    [
      [1, [null, null], [3,1]],
      [2, [2, 1], [null, null]],
      [3, [null, null], [5,1]],
      [4, [4, 0.5], [null, null]],
      [5, [null, null], [7,1]],
      [6, [NaN, NaN], [null, null]],
      [8, [8, 1], [null, null]],
      [10, [10, 1], [null, null]]
    ];
  var g = new Dygraph(graph, data,
        {
          labels: ['x', 'A', 'B' ],
          connectSeparatedPoints: true,
          drawPoints: true,
          errorBars: true
        }
      );

  var in_series = g.dataHandler_.extractSeries(data, 1, g.attributes_);

  assertEquals(null, in_series[4][1]);
  assertEquals(null, in_series[4][2][0]);
  assertEquals(null, in_series[4][2][1]);
  assertNaN(in_series[5][1]);
  assertNaN(in_series[5][2][0]);
  assertNaN(in_series[5][2][1]);

  var out_series = g.dataHandler_.rollingAverage(in_series, 1, g.attributes_);
  assertNaN(out_series[5][1]);
  assertNaN(out_series[5][2][0]);
  assertNaN(out_series[5][2][1]);
  assertEquals(null, out_series[4][1]);
  assertEquals(null, out_series[4][2][0]);
  assertEquals(null, out_series[4][2][1]);
};
