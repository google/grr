/**
 * @fileoverview Test cases for the option "connectSeparatedPoints" especially for the scenario where not every series has a value for each timestamp.
 *
 * @author julian.eichstaedt@ch.sauter-bc.com (Fr. Sauter AG)
 */
var ConnectSeparatedPointsTestCase = TestCase("connect-separated-points");

ConnectSeparatedPointsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

ConnectSeparatedPointsTestCase.origFunc = Dygraph.getContext;

ConnectSeparatedPointsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
  Dygraph.getContext = function(canvas) {
    return new Proxy(ConnectSeparatedPointsTestCase.origFunc(canvas));
  };
};

ConnectSeparatedPointsTestCase.prototype.tearDown = function() {
  Dygraph.getContext = ConnectSeparatedPointsTestCase.origFunc;
};

ConnectSeparatedPointsTestCase.prototype.testEdgePointsSimple = function() {
  var opts = {
    width: 480,
    height: 320,
    labels: ["x", "series1", "series2", "additionalSeries"],
    connectSeparatedPoints: true,
    dateWindow: [2.5,7.5]
  };

  var data = [
              [0,-1,0,null],
              [1,null,2,null],
              [2,null,4,null],
              [3,0.5,0,null],
              [4,1,-1,5],
              [5,2,-2,6],
              [6,2.5,-2.5,7],
              [7,3,-3,null],
              [8,4,null,null],
              [9,4,-10,null]
             ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  
  htx = g.hidden_ctx_;

  var attrs = {};  

  // Test if series1 is drawn correctly.
  // ------------------------------------
  
  // The first point of the first series
  var x1 = data[0][0];
  var y1 = data[0][1];
  var xy1 = g.toDomCoords(x1, y1);
  
  // The next valid point of this series
  var x2 = data[3][0];
  var y2 = data[3][1];
  var xy2 = g.toDomCoords(x2, y2);
  
  // Check if both points are connected at the left edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

  // Test if series2 is drawn correctly.
  // ------------------------------------

  // The last point of the second series.
  var x2 = data[9][0];
  var y2 = data[9][2];
  var xy2 = g.toDomCoords(x2, y2);

  // The previous valid point of this series
  var x1 = data[7][0];
  var y1 = data[7][2];
  var xy1 = g.toDomCoords(x1, y1);
  
  // Check if both points are connected at the right edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
};

ConnectSeparatedPointsTestCase.prototype.testEdgePointsCustomBars = function() {
  var opts = {
    width: 480,
    height: 320,
    labels: ["x", "series1", "series2", "additionalSeries"],
    connectSeparatedPoints: true,
    dateWindow: [2.5,7.5],
    customBars: true
  };
  
  var data = [
              [0,[4,5,6], [1,2,3], [null, null, null]],
              [1,[null,null,null], [2,3,4], [null, null, null]],
              [2,[null,null,null], [3,4,5], [null, null, null]],
              [3,[0,1,2], [2,3,4], [null, null, null]],    
              [4,[1,2,3], [2,3,4], [4, 5, 6]],
              [5,[1,2,3], [3,4,5], [4, 5, 6]],
              [6,[0,1,2], [4,5,6], [5, 6, 7]],
              [7,[0,1,2], [4,5,6], [null, null, null]],
              [8,[2,3,4], [null,null,null], [null, null, null]],
              [9,[0,1,2], [2,4,9], [null, null, null]]
              
             ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  
  htx = g.hidden_ctx_;

  var attrs = {};  

  
  // Test if values of the series1 are drawn correctly.
  // ------------------------------------
  
  // The first point of the first series
  var x1 = data[0][0];
  var y1 = data[0][1][1];
  var xy1 = g.toDomCoords(x1, y1);
  
  // The next valid point of this series
  var x2 = data[3][0];
  var y2 = data[3][1][1];
  var xy2 = g.toDomCoords(x2, y2);
  
  // Check if both points are connected at the left edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // Test if the custom bars of the series1 are drawn correctly
  // --------------------------------------------
  
  // The first min-point of this series
  x1 = data[0][0];
  y1 = data[0][1][0];
  xy1 = g.toDomCoords(x1, y1);

  // The next valid min-point of the second series.
  x2 = data[3][0];
  y2 = data[3][1][0];
  xy2 = g.toDomCoords(x2, y2);
  
  // Check if both points are connected at the left edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // The first max-point of this series
  x1 = data[0][0];
  y1 = data[0][1][2];
  xy1 = g.toDomCoords(x1, y1);
  
  // The next valid max-point of the second series.
  x2 = data[3][0];
  y2 = data[3][1][2];
  xy2 = g.toDomCoords(x2, y2);
  
  // Check if both points are connected at the left edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // Test if values of the series2 are drawn correctly.
  // ------------------------------------
  
  // The last point of the second series.
  var x2 = data[9][0];
  var y2 = data[9][2][1];
  var xy2 = g.toDomCoords(x2, y2);
  
  // The previous valid point of this series
  var x1 = data[7][0];
  var y1 = data[7][2][1];
  var xy1 = g.toDomCoords(x1, y1);
  
  // Check if both points are connected at the right edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // Test if the custom bars of the series2 are drawn correctly
  // --------------------------------------------
  
  // The last min-point of the second series.
  x2 = data[9][0];
  y2 = data[9][2][0];
  xy2 = g.toDomCoords(x2, y2);
  
  // The previous valid min-point of this series
  x1 = data[7][0];
  y1 = data[7][2][0];
  xy1 = g.toDomCoords(x1, y1);
  
  // Check if both points are connected at the right edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // The last max-point of the second series.
  x2 = data[9][0];
  y2 = data[9][2][2];
  xy2 = g.toDomCoords(x2, y2);
  
  // The previous valid max-point of this series
  x1 = data[7][0];
  y1 = data[7][2][2];
  xy1 = g.toDomCoords(x1, y1);
  
  // Check if both points are connected at the right edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
};

ConnectSeparatedPointsTestCase.prototype.testEdgePointsErrorBars = function() {
  var opts = {
    width: 480,
    height: 320,
    labels: ["x", "series1", "series2", "seriesTestHelper"],
    connectSeparatedPoints: true,
    dateWindow: [2,7.5],
    errorBars: true
    
  };
  
  var data = [
              [0,[5,1], [2,1], [null,null]],
              [1,[null,null], [3,1], [null,null]],
              [2,[null,null], [4,1], [null,null]],
              [3,[1,1], [3,1], [null,null]],    
              [4,[2,1], [3,1], [5,1]],
              [5,[2,1], [4,1], [5,1]],
              [6,[1,1], [5,1], [6,1]],
              [7,[1,1], [5,1], [null,null]],
              [8,[3,1], [null,null], [null,null]],
              [9,[1,1], [4,1], [null,null]]
              
             ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  
  htx = g.hidden_ctx_;

  var attrs = {};  

  
  // Test if values of the series1 are drawn correctly.
  // ------------------------------------
  
  // The first point of the first series
  var x1 = data[0][0];
  var y1 = data[0][1][0];
  var xy1 = g.toDomCoords(x1, y1);
  
  // The next valid point of this series
  var x2 = data[3][0];
  var y2 = data[3][1][0];
  var xy2 = g.toDomCoords(x2, y2);
  
  // Check if both points are connected at the left edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // Test if the upper error bars of series1 are drawn correctly
  // --------------------------------------------
  
  // The first upper error-point of this series
  x1 = data[0][0];
  var y1error = y1 + (data[0][1][1]*2);
  xy1 = g.toDomCoords(x1, y1error);
  
  // The next valid upper error-point of the second series.
  x2 = data[3][0];
  var y2error = y2 + (data[3][1][1]*2);
  xy2 = g.toDomCoords(x2, y2error);
  
  // Check if both points are connected at the left edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // Test if the lower error bars of series1 are drawn correctly
  // --------------------------------------------
  
  // The first lower error-point of this series
  x1 = data[0][0];
  y1error = y1 - (data[0][1][1]*2);
  xy1 = g.toDomCoords(x1, y1error);
  
  //The next valid lower error-point of the second series.
  x2 = data[3][0];
  y2error = y2 - (data[3][1][1]*2);
  xy2 = g.toDomCoords(x2, y2error);
  
  // Check if both points are connected at the left edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  
  // Test if values of the series2 are drawn correctly.
  // ------------------------------------
  
  // The last point of this series
  x2 = data[9][0];
  y2 = data[9][2][0];
  xy2 = g.toDomCoords(x2, y2);
  
  // The previous valid point of the first series
  x1 = data[7][0];
  y1 = data[7][2][0];
  xy1 = g.toDomCoords(x1, y1);
  
  // Check if both points are connected at the right edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // Test if the upper error bars of series2 are drawn correctly
  // --------------------------------------------
  
  // The last upper error-point of the second series.
  x2 = data[9][0];
  var y2error = y2 + (data[9][2][1]*2);
  xy2 = g.toDomCoords(x2, y2error);
  
  // The previous valid upper error-point of this series
  x1 = data[7][0];
  var y1error = y1 + (data[7][2][1]*2);
  xy1 = g.toDomCoords(x1, y1error);
  
  // Check if both points are connected at the right edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  
  // Test if the lower error bars of series1 are drawn correctly
  // --------------------------------------------
  
  // The last lower error-point of the second series.
  x2 = data[9][0];
  y2error = y2 - (data[9][2][1]*2);
  xy2 = g.toDomCoords(x2, y2error);
  
  // The previous valid lower error-point of this series
  x1 = data[7][0];
  y1error = y1 - (data[7][2][1]*2);
  xy1 = g.toDomCoords(x1, y1error);
  
  // Check if both points are connected at the right edge of the canvas and if the option "connectSeparatedPoints" works properly
  // even if the point is outside the visible range and only one series has a valid value for this point.
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
};

ConnectSeparatedPointsTestCase.prototype.testConnectSeparatedPointsPerSeries = function() {
  var assertExpectedLinesDrawnPerSeries = function(htx, expectedSeries1, expectedSeries2, expectedSeries3) {
    var expected = [expectedSeries1, expectedSeries2, expectedSeries3];    
    var actual = [ 
        CanvasAssertions.numLinesDrawn(htx, "#ff0000"),
        CanvasAssertions.numLinesDrawn(htx, "#00ff00"),
        CanvasAssertions.numLinesDrawn(htx, "#0000ff")];
    assertEquals(expected, actual);
  }

  var g = new Dygraph(document.getElementById("graph"),
      [
        [1, 10, 10, 10],
        [2, 15, 11, 12],
        [3, null, null, 12],
        [4, 20, 14, null],
        [5, 15, null, 17],
        [6, 18, null, null],
        [7, 12, 14, null]
      ],
      {
        labels: ["Date","Series1","Series2","Series3"],
        connectSeparatedPoints: false,
        colors: ["#ff0000", "#00ff00", "#0000ff"]
      });

  htx = g.hidden_ctx_;
  assertExpectedLinesDrawnPerSeries(htx, 4, 1, 2);

  Proxy.reset(htx);
  g.updateOptions({
    connectSeparatedPoints : true,
  });
  assertExpectedLinesDrawnPerSeries(htx, 5, 3, 3);

  Proxy.reset(htx);
  g.updateOptions({
    connectSeparatedPoints : false,
    series : {
      Series1 : { connectSeparatedPoints : true }
    }
  });
  assertExpectedLinesDrawnPerSeries(htx, 5, 1, 2);


  Proxy.reset(htx);
  g.updateOptions({
    connectSeparatedPoints : true,
    series : {
      Series1 : { connectSeparatedPoints : false }
    }
  });
  assertExpectedLinesDrawnPerSeries(htx, 4, 3, 3);
}

ConnectSeparatedPointsTestCase.prototype.testNaNErrorBars = function() {
  var data = [
    [0,[1,2,3]],
    [1,[2,3,4]],
    [2,[3,4,5]],
    [3,[null,null,null]],
    [4,[2,3,4]],
    [5,[3,4,5]],
    [6,[2,3,4]],
    [7,[NaN,NaN,NaN]],
    [8,[2,3,4]],
    [9,[2,3,4]],
    [10,[2,3,4]],
    [11,[2,3,4]]
  ];
    
  var opts = {
    labels: ["x", "y"],
    colors: ["#ff0000"],
    customBars: true,
    connectSeparatedPoints: true
  };
  
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  
  htx = g.hidden_ctx_;

  var attrs = {};  
  
  // Line should be drawn across the null gap.
  CanvasAssertions.assertLineDrawn(htx, 
	g.toDomCoords(data[2][0], data[2][1][1]),
	g.toDomCoords(data[4][0], data[4][1][1]),
        attrs);

  // No line across the NaN gap, and a single line (not two)
  // across the null gap.
  assertEquals(8, CanvasAssertions.numLinesDrawn(htx, '#ff0000'));
};
