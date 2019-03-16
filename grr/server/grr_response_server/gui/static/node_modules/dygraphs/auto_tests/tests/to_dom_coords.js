/** 
 * @fileoverview Test cases for toDomCoords/toDataCoords
 *
 * @author danvk@google.com (Dan Vanderkam)
 */

var ToDomCoordsTestCase = TestCase("to-dom-coords");

ToDomCoordsTestCase._origFunc = Dygraph.getContext;
ToDomCoordsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
  Dygraph.getContext = function(canvas) {
    return new Proxy(ToDomCoordsTestCase._origFunc(canvas));
  }
};

ToDomCoordsTestCase.prototype.tearDown = function() {
  Dygraph.getContext = ToDomCoordsTestCase._origFunc;
};

// Checks that toDomCoords and toDataCoords are inverses of one another.
ToDomCoordsTestCase.prototype.checkForInverses = function(g) {
  var x_range = g.xAxisRange();
  var y_range = g.yAxisRange();
  for (var i = 0; i <= 10; i++) {
    var x = x_range[0] + i / 10.0 * (x_range[1] - x_range[0]);
    for (var j = 0; j <= 10; j++) {
      var y = y_range[0] + j / 10.0 * (y_range[1] - y_range[0]);
      assertEquals(x, g.toDataXCoord(g.toDomXCoord(x)));
      assertEquals(y, g.toDataYCoord(g.toDomYCoord(y)));
    }
  }
}

ToDomCoordsTestCase.prototype.testPlainChart = function() {
  var opts = {
    axes : {
      x : {
        drawAxis : false,
        drawGrid : false,
      },
      y : {
        drawAxis : false,
        drawGrid : false,
      }
    },
    rightGap: 0,
    valueRange: [0, 100],
    dateWindow: [0, 100],
    width: 400,
    height: 400,
    colors: ['#ff0000']
  }

  var graph = document.getElementById("graph");
  g = new Dygraph(graph, [ [0,0], [100,100] ], opts);

  assertEquals([0, 100], g.toDataCoords(0, 0));
  assertEquals([0, 0], g.toDataCoords(0, 400));
  assertEquals([100, 100], g.toDataCoords(400, 0));
  assertEquals([100, 0], g.toDataCoords(400, 400));

  this.checkForInverses(g);

  // TODO(konigsberg): This doesn't really belong here. Move to its own test.
  var htx = g.hidden_ctx_;
  assertEquals(1, CanvasAssertions.numLinesDrawn(htx, '#ff0000'));
}

ToDomCoordsTestCase.prototype.testChartWithAxes = function() {
  var opts = {
    drawXAxis: true,
    xAxisHeight: 50,
    drawYAxis: true,
    yAxisLabelWidth: 100,
    axisTickSize: 0,
    drawXGrid: false,
    drawYGrid: false,
    rightGap: 0,
    valueRange: [0, 100],
    dateWindow: [0, 100],
    width: 500,
    height: 450,
    colors: ['#ff0000']
  }

  var graph = document.getElementById("graph");
  g = new Dygraph(graph, [ [0,0], [100,100] ], opts);

  assertEquals([0, 100], g.toDataCoords(100, 0));
  assertEquals([0, 0], g.toDataCoords(100, 400));
  assertEquals([100, 100], g.toDataCoords(500, 0));
  assertEquals([100, 0], g.toDataCoords(500, 400));

  this.checkForInverses(g);
}

ToDomCoordsTestCase.prototype.testChartWithAxesAndLabels = function() {
  var opts = {
    drawXAxis: true,
    xAxisHeight: 50,
    drawYAxis: true,
    yAxisLabelWidth: 100,
    axisTickSize: 0,
    drawXGrid: false,
    drawYGrid: false,
    rightGap: 0,
    valueRange: [0, 100],
    dateWindow: [0, 100],
    width: 500,
    height: 500,
    colors: ['#ff0000'],
    ylabel: 'This is the y-axis',
    xlabel: 'This is the x-axis',
    xLabelHeight: 25,
    title: 'This is the title of the chart',
    titleHeight: 25
  }

  var graph = document.getElementById("graph");
  g = new Dygraph(graph, [ [0,0], [100,100] ], opts);

  assertEquals([0, 100], g.toDataCoords(100, 25));
  assertEquals([0, 0], g.toDataCoords(100, 425));
  assertEquals([100, 100], g.toDataCoords(500, 25));
  assertEquals([100, 0], g.toDataCoords(500, 425));

  this.checkForInverses(g);
}

ToDomCoordsTestCase.prototype.testYAxisLabelWidth = function() {
  var opts = {
    yAxisLabelWidth: 100,
    axisTickSize: 0,
    rightGap: 0,
    valueRange: [0, 100],
    dateWindow: [0, 100],
    width: 500,
    height: 500
  }

  var graph = document.getElementById("graph");
  g = new Dygraph(graph, [ [0,0], [100,100] ], opts);

  assertEquals([100, 0], g.toDomCoords(0, 100));
  assertEquals([500, 486], g.toDomCoords(100, 0));

  g.updateOptions({ yAxisLabelWidth: 50 });
  assertEquals([50, 0], g.toDomCoords(0, 100));
  assertEquals([500, 486], g.toDomCoords(100, 0));
}

ToDomCoordsTestCase.prototype.testAxisTickSize = function() {
  var opts = {
    yAxisLabelWidth: 100,
    axisTickSize: 0,
    rightGap: 0,
    valueRange: [0, 100],
    dateWindow: [0, 100],
    width: 500,
    height: 500
  }

  var graph = document.getElementById("graph");
  g = new Dygraph(graph, [ [0,0], [100,100] ], opts);

  assertEquals([100, 0], g.toDomCoords(0, 100));
  assertEquals([500, 486], g.toDomCoords(100, 0));

  g.updateOptions({ axisTickSize : 50 });
  assertEquals([200, 0], g.toDomCoords(0, 100));
  assertEquals([500, 386], g.toDomCoords(100, 0));
}

ToDomCoordsTestCase.prototype.testChartLogarithmic_YAxis = function() {
  var opts = {
    rightGap: 0,
    valueRange: [1, 4],
    dateWindow: [0, 10],
    width: 400,
    height: 400,
    colors: ['#ff0000'],
    axes: {
      x: {
        drawGrid: false,
        drawAxis: false
      },
      y: {
        drawGrid: false,
        drawAxis: false,
        logscale: true
      }
    }
  }

  var graph = document.getElementById("graph");
  g = new Dygraph(graph, [ [1,1], [4,4] ], opts);

  var epsilon = 1e-8;
  assertEqualsDelta([0, 4], g.toDataCoords(0, 0), epsilon);
  assertEqualsDelta([0, 1], g.toDataCoords(0, 400), epsilon);
  assertEqualsDelta([10, 4], g.toDataCoords(400, 0), epsilon);
  assertEqualsDelta([10, 1], g.toDataCoords(400, 400), epsilon);
  assertEqualsDelta([10, 2], g.toDataCoords(400, 200), epsilon);
  
  assertEquals([0, 0], g.toDomCoords(0, 4));
  assertEquals([0, 400], g.toDomCoords(0, 1));
  assertEquals([400, 0], g.toDomCoords(10, 4));
  assertEquals([400, 400], g.toDomCoords(10, 1));
  assertEquals([400, 200], g.toDomCoords(10, 2));
}

ToDomCoordsTestCase.prototype.testChartLogarithmic_XAxis = function() {
  var opts = {
    rightGap: 0,
    valueRange: [1, 1000],
    dateWindow: [1, 1000],
    width: 400,
    height: 400,
    colors: ['#ff0000'],
    axes: {
      x: {
        drawGrid: false,
        drawAxis: false,
        logscale: true
      },
      y: {
        drawGrid: false,
        drawAxis: false
      }
    }
  }

  var graph = document.getElementById("graph");
  g = new Dygraph(graph, [ [1,1], [10, 10], [100,100], [1000,1000] ], opts);

  var epsilon = 1e-8;
  assertEqualsDelta(1, g.toDataXCoord(0), epsilon);
  assertEqualsDelta(5.623413251903489, g.toDataXCoord(100), epsilon);
  assertEqualsDelta(31.62277660168378, g.toDataXCoord(200), epsilon);
  assertEqualsDelta(177.8279410038921, g.toDataXCoord(300), epsilon);
  assertEqualsDelta(1000, g.toDataXCoord(400), epsilon);

  assertEqualsDelta(0, g.toDomXCoord(1), epsilon);
  assertEqualsDelta(3.6036036036036037, g.toDomXCoord(10), epsilon);
  assertEqualsDelta(39.63963963963964, g.toDomXCoord(100), epsilon);
  assertEqualsDelta(400, g.toDomXCoord(1000), epsilon);

  assertEqualsDelta(0, g.toPercentXCoord(1), epsilon);
  assertEqualsDelta(0.3333333333, g.toPercentXCoord(10), epsilon);
  assertEqualsDelta(0.6666666666, g.toPercentXCoord(100), epsilon);
  assertEqualsDelta(1, g.toPercentXCoord(1000), epsilon);
 
  // Now zoom in and ensure that the methods return reasonable values.
  g.updateOptions({dateWindow: [ 10, 100 ]});

  assertEqualsDelta(10, g.toDataXCoord(0), epsilon);
  assertEqualsDelta(17.78279410038923, g.toDataXCoord(100), epsilon);
  assertEqualsDelta(31.62277660168379, g.toDataXCoord(200), epsilon);
  assertEqualsDelta(56.23413251903491, g.toDataXCoord(300), epsilon);
  assertEqualsDelta(100, g.toDataXCoord(400), epsilon);

  assertEqualsDelta(-40, g.toDomXCoord(1), epsilon);
  assertEqualsDelta(0, g.toDomXCoord(10), epsilon);
  assertEqualsDelta(400, g.toDomXCoord(100), epsilon);
  assertEqualsDelta(4400, g.toDomXCoord(1000), epsilon);

  assertEqualsDelta(-1, g.toPercentXCoord(1), epsilon);
  assertEqualsDelta(0, g.toPercentXCoord(10), epsilon);
  assertEqualsDelta(1, g.toPercentXCoord(100), epsilon);
  assertEqualsDelta(2, g.toPercentXCoord(1000), epsilon);
}