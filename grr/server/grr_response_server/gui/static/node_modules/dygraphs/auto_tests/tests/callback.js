/**
 * @fileoverview Test cases for the callbacks.
 *
 * @author uemit.seren@gmail.com (Ümit Seren)
 */

var CallbackTestCase = TestCase("callback");

CallbackTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div><div id='selection'></div>";
  this.xhr = XMLHttpRequest;
  this.styleSheet = document.createElement("style");
  this.styleSheet.type = "text/css";
  document.getElementsByTagName("head")[0].appendChild(this.styleSheet);
};

CallbackTestCase.prototype.tearDown = function() {
  XMLHttpRequest = this.xhr;
};

var data = "X,a\,b,c\n" +
 "10,-1,1,2\n" +
 "11,0,3,1\n" +
 "12,1,4,2\n" +
 "13,0,2,3\n";


/**
 * This tests that when the function idxToRow_ returns the proper row and the onHiglightCallback
 * is properly called when the  first series is hidden (setVisibility = false)
 *
 */
CallbackTestCase.prototype.testHighlightCallbackIsCalled = function() {
  var h_row;
  var h_pts;

  var highlightCallback = function(e, x, pts, row) {
    assertEquals(g, this);
    h_row = row;
    h_pts = pts;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data,
      {
        width: 100,
        height: 100,
        visibility: [false, true, true],
        highlightCallback: highlightCallback
      });

  DygraphOps.dispatchMouseMove(g, 13, 10);

  //check correct row is returned
  assertEquals(3, h_row);
  //check there are only two points (because first series is hidden)
  assertEquals(2, h_pts.length);
};


/**
 * Test that drawPointCallback isn't called when drawPoints is false
 */
CallbackTestCase.prototype.testDrawPointCallback_disabled = function() {
  var called = false;

  var callback = function() {
    assertEquals(g, this);
    called = true;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, {
      drawPointCallback: callback,
    });

  assertFalse(called);
};

/**
 * Test that drawPointCallback is called when drawPoints is true
 */
CallbackTestCase.prototype.testDrawPointCallback_enabled = function() {
  var called = false;
  var callbackThis = null;

  var callback = function() {
    callbackThis = this;
    called = true;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, {
      drawPoints: true,
      drawPointCallback: callback
    });

  assertTrue(called);
  assertEquals(g, callbackThis);
};

/**
 * Test that drawPointCallback is called when drawPoints is true
 */
CallbackTestCase.prototype.testDrawPointCallback_pointSize = function() {
  var pointSize = 0;
  var count = 0;

  var callback = function(g, seriesName, canvasContext, cx, cy, color, pointSizeParam) {
    assertEquals(g, this);
    pointSize = pointSizeParam;
    count++;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, {
      drawPoints: true,
      drawPointCallback: callback
    });

  assertEquals(1.5, pointSize);
  assertEquals(12, count); // one call per data point.

  var g = new Dygraph(graph, data, {
      drawPoints: true,
      drawPointCallback: callback,
      pointSize: 8
    });

  assertEquals(8, pointSize);
};

/**
 * Test that drawPointCallback is called for isolated points when
 * drawPoints is false, and also for gap points if that's enabled.
 */
CallbackTestCase.prototype.testDrawPointCallback_isolated = function() {
  var xvalues = [];

  var g;
  var callback = function(g, seriesName, canvasContext, cx, cy, color, pointSizeParam) {
    assertEquals(g, this);
    var dx = g.toDataXCoord(cx);
    xvalues.push(dx);
    Dygraph.Circles.DEFAULT.apply(this, arguments);
  };

  var graph = document.getElementById("graph");
  var testdata = [[10, 2], [11, 3], [12, NaN], [13, 2], [14, NaN], [15, 3]];
  var graphOpts = {
      labels: ['X', 'Y'],
      valueRange: [0, 4],
      drawPoints : false,
      drawPointCallback : callback,
      pointSize : 8
  };

  // Test that isolated points get drawn
  g = new Dygraph(graph, testdata, graphOpts);
  assertEquals(2, xvalues.length);
  assertEquals(13, xvalues[0]);
  assertEquals(15, xvalues[1]);

  // Test that isolated points + gap points get drawn when
  // drawGapEdgePoints is set.  This should add one point at the right
  // edge of the segment at x=11, but not at the graph edge at x=10.
  xvalues = []; // Reset for new test
  graphOpts.drawGapEdgePoints = true;
  g = new Dygraph(graph, testdata, graphOpts);
  assertEquals(3, xvalues.length);
  assertEquals(11, xvalues[0]);
  assertEquals(13, xvalues[1]);
  assertEquals(15, xvalues[2]);
};

/**
 * This tests that when the function idxToRow_ returns the proper row and the onHiglightCallback
 * is properly called when the first series is hidden (setVisibility = false)
 *
 */
CallbackTestCase.prototype.testDrawHighlightPointCallbackIsCalled = function() {
  var called = false;

  var drawHighlightPointCallback = function() {
    assertEquals(g, this);
    called = true;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data,
      {
        width: 100,
        height: 100,
        drawHighlightPointCallback: drawHighlightPointCallback
      });

  assertFalse(called);
  DygraphOps.dispatchMouseMove(g, 13, 10);
  assertTrue(called);
};

/**
 * Test the closest-series highlighting methods for normal and stacked modes.
 * Also pass in line widths for plain and highlighted lines for easier visual
 * confirmation that the highlighted line is drawn on top of the others.
 */
var runClosestTest = function(isStacked, widthNormal, widthHighlighted) {
  var h_row;
  var h_pts;
  var h_series;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data,
      {
        width: 600,
        height: 400,
        visibility: [false, true, true],
        stackedGraph: isStacked,
        strokeWidth: widthNormal,
        strokeBorderWidth: 2,
        highlightCircleSize: widthNormal * 2,
        highlightSeriesBackgroundAlpha: 0.3,

        highlightSeriesOpts: {
          strokeWidth: widthHighlighted,
          highlightCircleSize: widthHighlighted * 2
        }
      });

  var highlightCallback = function(e, x, pts, row, set) {
    assertEquals(g, this);
    h_row = row;
    h_pts = pts;
    h_series = set;
    document.getElementById('selection').innerHTML='row=' + row + ', set=' + set;
  };

  g.updateOptions({highlightCallback: highlightCallback}, true);

  if (isStacked) {
    DygraphOps.dispatchMouseMove(g, 11.45, 1.4);
    assertEquals(1, h_row);
    assertEquals('c', h_series);

    //now move up in the same row
    DygraphOps.dispatchMouseMove(g, 11.45, 1.5);
    assertEquals(1, h_row);
    assertEquals('b', h_series);

    //and a bit to the right
    DygraphOps.dispatchMouseMove(g, 11.55, 1.5);
    assertEquals(2, h_row);
    assertEquals('c', h_series);
  } else {
    DygraphOps.dispatchMouseMove(g, 11, 1.5);
    assertEquals(1, h_row);
    assertEquals('c', h_series);

    //now move up in the same row
    DygraphOps.dispatchMouseMove(g, 11, 2.5);
    assertEquals(1, h_row);
    assertEquals('b', h_series);
  }

  return g;
};

/**
 * Test basic closest-point highlighting.
 */
CallbackTestCase.prototype.testClosestPointCallback = function() {
  runClosestTest(false, 1, 3);
}

/**
 * Test setSelection() with series name
 */
CallbackTestCase.prototype.testSetSelection = function() {
  var g = runClosestTest(false, 1, 3);
  assertEquals(1, g.attr_('strokeWidth', 'c'));
  g.setSelection(false, 'c');
  assertEquals(3, g.attr_('strokeWidth', 'c'));
}

/**
 * Test closest-point highlighting for stacked graph
 */
CallbackTestCase.prototype.testClosestPointStackedCallback = function() {
  runClosestTest(true, 1, 3);
}

/**
 * Closest-point highlighting with legend CSS - border around active series.
 */
CallbackTestCase.prototype.testClosestPointCallbackCss1 = function() {
  var css = "div.dygraph-legend > span { display: block; }\n" +
      "div.dygraph-legend > span.highlight { border: 1px solid grey; }\n";
  this.styleSheet.innerHTML = css;
  runClosestTest(false, 2, 4);
  this.styleSheet.innerHTML = '';
}

/**
 * Closest-point highlighting with legend CSS - show only closest series.
 */
CallbackTestCase.prototype.testClosestPointCallbackCss2 = function() {
  var css = "div.dygraph-legend > span { display: none; }\n" +
      "div.dygraph-legend > span.highlight { display: inline; }\n";
  this.styleSheet.innerHTML = css;
  runClosestTest(false, 10, 15);
  this.styleSheet.innerHTML = '';
  // TODO(klausw): verify that the highlighted line is drawn on top?
}

/**
 * Closest-point highlighting with locked series.
 */
CallbackTestCase.prototype.testSetSelectionLocking = function() {
  var g = runClosestTest(false, 2, 4);

  // Default behavior, 'b' is closest
  DygraphOps.dispatchMouseMove(g, 11, 4);
  assertEquals('b', g.getHighlightSeries());

  // Now lock selection to 'c'
  g.setSelection(false, 'c', true);
  DygraphOps.dispatchMouseMove(g, 11, 4);
  assertEquals('c', g.getHighlightSeries());

  // Unlock, should be back to 'b'
  g.clearSelection();
  DygraphOps.dispatchMouseMove(g, 11, 4);
  assertEquals('b', g.getHighlightSeries());
}

/**
 * This tests that closest point searches work for data containing NaNs.
 *
 * It's intended to catch a regression where a NaN Y value confuses the
 * closest-point algorithm, treating it as closer as any previous point.
 */
CallbackTestCase.prototype.testNaNData = function() {
  var dataNaN = [
    [9, -1, NaN, NaN],
    [10, -1, 1, 2],
    [11, 0, 3, 1],
    [12, 1, 4, NaN],
    [13, 0, 2, 3],
    [14, -1, 1, 4]];

  var h_row;
  var h_pts;

  var highlightCallback = function(e, x, pts, row) {
    assertEquals(g, this);
    h_row = row;
    h_pts = pts;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, dataNaN,
      {
        width: 600,
        height: 400,
        labels: ['x', 'a', 'b', 'c'],
        visibility: [false, true, true],
        highlightCallback: highlightCallback
      });

  DygraphOps.dispatchMouseMove(g, 10.1, 0.9);
  //check correct row is returned
  assertEquals(1, h_row);

  // Explicitly test closest point algorithms
  var dom = g.toDomCoords(10.1, 0.9);
  assertEquals(1, g.findClosestRow(dom[0]));

  var res = g.findClosestPoint(dom[0], dom[1]);
  assertEquals(1, res.row);
  assertEquals('b', res.seriesName);

  res = g.findStackedPoint(dom[0], dom[1]);
  assertEquals(1, res.row);
  assertEquals('c', res.seriesName);
};

/**
 * This tests that stacked point searches work for data containing NaNs.
 */
CallbackTestCase.prototype.testNaNDataStack = function() {
  var dataNaN = [
    [9, -1, NaN, NaN],
    [10, -1, 1, 2],
    [11, 0, 3, 1],
    [12, 1, NaN, 2],
    [13, 0, 2, 3],
    [14, -1, 1, 4],
    [15, 0, 2, NaN],
    [16, 1, 1, 3],
    [17, 1, NaN, 3],
    [18, 0, 2, 5],
    [19, 0, 1, 4]];

  var h_row;
  var h_pts;

  var highlightCallback = function(e, x, pts, row) {
    assertEquals(g, this);
    h_row = row;
    h_pts = pts;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, dataNaN,
      {
        width: 600,
        height: 400,
        labels: ['x', 'a', 'b', 'c'],
        visibility: [false, true, true],
        stackedGraph: true,
        highlightCallback: highlightCallback
      });

  DygraphOps.dispatchMouseMove(g, 10.1, 0.9);
  //check correct row is returned
  assertEquals(1, h_row);

  // Explicitly test stacked point algorithm.
  var dom = g.toDomCoords(10.1, 0.9);
  var res = g.findStackedPoint(dom[0], dom[1]);
  assertEquals(1, res.row);
  assertEquals('c', res.seriesName);

  // All-NaN area at left, should get no points.
  dom = g.toDomCoords(9.1, 0.9);
  res = g.findStackedPoint(dom[0], dom[1]);
  assertEquals(0, res.row);
  assertEquals(undefined, res.seriesName);

  // First gap, get 'c' since it's non-NaN.
  dom = g.toDomCoords(12.1, 0.9);
  res = g.findStackedPoint(dom[0], dom[1]);
  assertEquals(3, res.row);
  assertEquals('c', res.seriesName);

  // Second gap, get 'b' since 'c' is NaN.
  dom = g.toDomCoords(15.1, 0.9);
  res = g.findStackedPoint(dom[0], dom[1]);
  assertEquals(6, res.row);
  assertEquals('b', res.seriesName);

  // Isolated points should work, finding series b in this case.
  dom = g.toDomCoords(15.9, 3.1);
  res = g.findStackedPoint(dom[0], dom[1]);
  assertEquals(7, res.row);
  assertEquals('b', res.seriesName);
};

CallbackTestCase.prototype.testGapHighlight = function() {
  var dataGap = [
    [1, null, 3],
    [2, 2, null],
    [3, null, 5],
    [4, 4, null],
    [5, null, 7],
    [6, NaN, null],
    [8, 8, null],
    [10, 10, null]];

  var h_row;
  var h_pts;

  var highlightCallback = function(e, x, pts, row) {
    assertEquals(g, this);
    h_row = row;
    h_pts = pts;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, dataGap, {
     width: 400,
     height: 300,
     //stackedGraph: true,
     connectSeparatedPoints: true,
     drawPoints: true,
     labels: ['x', 'A', 'B'],
     highlightCallback: highlightCallback
  });

  DygraphOps.dispatchMouseMove(g, 1.1, 10);
  //point from series B
  assertEquals(0, h_row);
  assertEquals(1, h_pts.length);
  assertEquals(3, h_pts[0].yval);
  assertEquals('B', h_pts[0].name);

  DygraphOps.dispatchMouseMove(g, 6.1, 10);
  // A is NaN at x=6
  assertEquals(1, h_pts.length);
  assert(isNaN(h_pts[0].yval));
  assertEquals('A', h_pts[0].name);

  DygraphOps.dispatchMouseMove(g, 8.1, 10);
  //point from series A
  assertEquals(6, h_row);
  assertEquals(1, h_pts.length);
  assertEquals(8, h_pts[0].yval);
  assertEquals('A', h_pts[0].name);
};

CallbackTestCase.prototype.testFailedResponse = function() {

  // Fake out the XMLHttpRequest so it doesn't do anything.
  XMLHttpRequest = function () {};
  XMLHttpRequest.prototype.open = function () {};
  XMLHttpRequest.prototype.send = function () {};

  var highlightCallback = function(e, x, pts, row) {
    fail("should not reach here");
  };

  var graph = document.getElementById("graph");
  graph.style.border = "2px solid black";
  var g = new Dygraph(graph, "data.csv", { // fake name
     width: 400,
     height: 300,
     highlightCallback : highlightCallback
  });

  DygraphOps.dispatchMouseOver_Point(g, 800, 800);
  DygraphOps.dispatchMouseMove_Point(g, 100, 100);
  DygraphOps.dispatchMouseMove_Point(g, 800, 800);

  var oldOnerror = window.onerror;
  var failed = false;
  window.onerror = function() { failed = true; return false; }

  DygraphOps.dispatchMouseOut_Point(g, 800, 800); // This call should not throw an exception.

  assertFalse("exception thrown during mouseout", failed);
};


// Regression test for http://code.google.com/p/dygraphs/issues/detail?id=355 
CallbackTestCase.prototype.testHighlightCallbackRow = function() {
  var highlightRow;
  var highlightCallback = function(e, x, pts, row) {
    assertEquals(g, this);
    highlightRow = row;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph,
    "X,Y,Z\n" +
    "0,1,2\n" +  // 0
    "1,2,3\n" +  // 100
    "2,3,4\n" +  // 200
    "3,4,5\n" +  // 300
    "4,5,6\n",   // 400
    { // fake name
       width: 400,
       height: 300,
       highlightCallback : highlightCallback
    });

  // Mouse over each of the points
  DygraphOps.dispatchMouseOver_Point(g, 0, 0);
  DygraphOps.dispatchMouseMove_Point(g, 0, 0);
  assertEquals(0, highlightRow);
  DygraphOps.dispatchMouseMove_Point(g, 100, 0);
  assertEquals(1, highlightRow);
  DygraphOps.dispatchMouseMove_Point(g, 200, 0);
  assertEquals(2, highlightRow);
  DygraphOps.dispatchMouseMove_Point(g, 300, 0);
  assertEquals(3, highlightRow);
  DygraphOps.dispatchMouseMove_Point(g, 400, 0);
  assertEquals(4, highlightRow);

  // Now zoom and verify that the row numbers still refer to rows in the data
  // array.
  g.updateOptions({dateWindow: [2, 4]});
  DygraphOps.dispatchMouseOver_Point(g, 0, 0);
  DygraphOps.dispatchMouseMove_Point(g, 0, 0);
  assertEquals(2, highlightRow);
  assertEquals('2: Y: 3 Z: 4', Util.getLegend());
};

/**
 * Test that underlay callback is called even when there are no series,
 * and that the y axis ranges are not NaN.
 */
CallbackTestCase.prototype.underlayCallback_noSeries = function() {
  var called = false;
  var yMin, yMax;

  var callback = function(canvas, area, g) {
    assertEquals(g, this);
    called = true;
    yMin = g.yAxisRange(0)[0];
    yMax = g.yAxisRange(0)[1];
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, "\n", {
      underlayCallback: callback
    });

  assertTrue(called);
  assertFalse(isNaN(yMin));
  assertFalse(isNaN(yMax));
};

/**
 * Test that underlay callback receives the correct y-axis range.
 */
CallbackTestCase.prototype.underlayCallback_yAxisRange = function() {
  var called = false;
  var yMin, yMax;

  var callback = function(canvas, area, g) {
    assertEquals(g, this);
    yMin = g.yAxisRange(0)[0];
    yMax = g.yAxisRange(0)[1];
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, "\n", {
      valueRange: [0,10],
      underlayCallback: callback
    });

  assertEquals(0, yMin);
  assertEquals(10, yMax);
};

/**
 * Test that drawPointCallback is called for isolated points and correct idx for the point is returned.
 */
CallbackTestCase.prototype.testDrawPointCallback_idx = function() {
  var indices = [];

  var g;
  var callback = function(g, seriesName, canvasContext, cx, cy, color, pointSizeParam,idx) {
    assertEquals(g, this);
    indices.push(idx);
    Dygraph.Circles.DEFAULT.apply(this, arguments);
  };

  var graph = document.getElementById("graph");

  var testdata = [[10, 2], [11, 3], [12, NaN], [13, 2], [14, NaN], [15, 3]];
  var graphOpts = {
      labels: ['X', 'Y'],
      valueRange: [0, 4],
      drawPoints : false,
      drawPointCallback : callback,
      pointSize : 8
  };

  // Test that correct idx for isolated points are passed to the callback.
  g = new Dygraph(graph, testdata, graphOpts);
  assertEquals(2, indices.length);
  assertEquals([3, 5],indices);

  // Test that correct indices for isolated points + gap points are passed to the callback when
  // drawGapEdgePoints is set.  This should add one point at the right
  // edge of the segment at x=11, but not at the graph edge at x=10.
  indices = []; // Reset for new test
  graphOpts.drawGapEdgePoints = true;
  g = new Dygraph(graph, testdata, graphOpts);
  assertEquals(3, indices.length);
  assertEquals([1, 3, 5],indices);


  //Test that correct indices are passed to the callback when zoomed in.
  indices = []; // Reset for new test
  graphOpts.dateWindow = [12.5,13.5]
  graphOpts.drawPoints = true;
  testdata = [[10, 2], [11, 3], [12, 4], [13, 2], [14, 5], [15, 3]];
  g = new Dygraph(graph, testdata, graphOpts);
  assertEquals(3, indices.length);
  assertEquals([2, 3, 4],indices);
};

/**
 * Test that the correct idx is returned for the point in the onHiglightCallback.
  */
CallbackTestCase.prototype.testDrawHighlightPointCallback_idx = function() {
  var idxToCheck = null;

  var drawHighlightPointCallback = function(g, seriesName, canvasContext, cx, cy, color, pointSizeParam,idx) {
    assertEquals(g, this);
    idxToCheck = idx;
  };
  var testdata = [[1, 2], [2, 3], [3, NaN], [4, 2], [5, NaN], [6, 3]];
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, testdata,
      {
          drawHighlightPointCallback : drawHighlightPointCallback
      });

  assertNull(idxToCheck);
  DygraphOps.dispatchMouseMove(g, 3, 0);
  // check that NaN point is not highlighted
  assertNull(idxToCheck);
  DygraphOps.dispatchMouseMove(g, 1, 2);
  // check that correct index is returned
  assertEquals(0,idxToCheck);
  DygraphOps.dispatchMouseMove(g, 6, 3);
  assertEquals(5,idxToCheck);
};
