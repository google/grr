/**
 * @fileoverview Tests for per-series options.
 *
 * @author danvk@google.com (Dan Vanderkam)
 */
var perSeriesTestCase = TestCase("per-series");

perSeriesTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

perSeriesTestCase.prototype.tearDown = function() {
};

perSeriesTestCase.prototype.testPerSeriesFill = function() {
  var opts = {
    width: 480,
    height: 320,
    drawXGrid: false,
    drawYGrid: false,
    drawXAxis: false,
    drawYAxis: false,
    series: {
      Y: { fillGraph: true },
    },
    colors: [ '#FF0000', '#0000FF' ],
    fillAlpha: 0.15
  };
  var data = "X,Y,Z\n" +
      "1,0,0\n" +
      "2,0,1\n" +
      "3,0,1\n" +
      "4,0,0\n" +
      "5,0,0\n" +
      "6,1,0\n" +
      "7,1,0\n" +
      "8,0,0\n"
  ;

  var graph = document.getElementById("graph");
  g = new Dygraph(graph, data, opts);

  var sampler = new PixelSampler(g);

  // Inside of the "Z" bump -- no fill.
  assertEquals([0,0,0,0], sampler.colorAtCoordinate(2.5, 0.5));

  // Inside of the "Y" bump -- filled in.
  assertEquals([255,0,0,38], sampler.colorAtCoordinate(6.5, 0.5));
};

perSeriesTestCase.prototype.testOldStyleSeries = function() {
  var opts = {
    pointSize : 5,
    Y: { pointSize : 4 },
  };
  var graph = document.getElementById("graph");
  var data = "X,Y,Z\n1,0,0\n";
  g = new Dygraph(graph, data, opts);

  assertEquals(5, g.getOption("pointSize"));
  assertEquals(4, g.getOption("pointSize", "Y"));
  assertEquals(5, g.getOption("pointSize", "Z"));
};

perSeriesTestCase.prototype.testNewStyleSeries = function() {
  var opts = {
    pointSize : 5,
    series : {
      Y: { pointSize : 4 }
    },
  };
  var graph = document.getElementById("graph");
  var data = "X,Y,Z\n1,0,0\n";
  g = new Dygraph(graph, data, opts);

  assertEquals(5, g.getOption("pointSize"));
  assertEquals(4, g.getOption("pointSize", "Y"));
  assertEquals(5, g.getOption("pointSize", "Z"));
};

perSeriesTestCase.prototype.testNewStyleSeriesTrumpsOldStyle = function() {
  var opts = {
    pointSize : 5,
    Z : { pointSize : 6 },
    series : {
      Y: { pointSize : 4 }
    },
  };
  var graph = document.getElementById("graph");
  var data = "X,Y,Z\n1,0,0\n";
  g = new Dygraph(graph, data, opts);

  assertEquals(5, g.getOption("pointSize"));
  assertEquals(4, g.getOption("pointSize", "Y"));
  assertEquals(5, g.getOption("pointSize", "Z"));

  // Erase the series object, and Z will become visible again.
  g.updateOptions({ series : undefined });
  assertEquals(5, g.getOption("pointSize"));
  assertEquals(6, g.getOption("pointSize", "Z"));
  assertEquals(5, g.getOption("pointSize", "Y"));
};

// TODO(konigsberg): move to multiple_axes.js
perSeriesTestCase.prototype.testAxisInNewSeries = function() {
  var opts = {
    series : {
      D : { axis : 'y2' },
      C : { axis : 1 },
      B : { axis : 0 },
      E : { axis : 'y' }
    }
  };
  var graph = document.getElementById("graph");
  var data = "X,A,B,C,D,E\n0,1,2,3,4,5\n";
  g = new Dygraph(graph, data, opts);

  assertEquals(["A", "B", "E"], g.attributes_.seriesForAxis(0));
  assertEquals(["C", "D"], g.attributes_.seriesForAxis(1));
};

// TODO(konigsberg): move to multiple_axes.js
perSeriesTestCase.prototype.testAxisInNewSeries_withAxes = function() {
  var opts = {
    series : {
      D : { axis : 'y2' },
      C : { axis : 1 },
      B : { axis : 0 },
      E : { axis : 'y' }
    },
    axes : {
      y : { pointSize : 7 },
      y2 : { pointSize  : 6 }
    }
  };
  var graph = document.getElementById("graph");
  var data = "X,A,B,C,D,E\n0,1,2,3,4,5\n";
  g = new Dygraph(graph, data, opts);

  assertEquals(["A", "B", "E"], g.attributes_.seriesForAxis(0));
  assertEquals(["C", "D"], g.attributes_.seriesForAxis(1));

  assertEquals(1.5, g.getOption("pointSize"));
  assertEquals(7, g.getOption("pointSize", "A"));
  assertEquals(7, g.getOption("pointSize", "B"));
  assertEquals(6, g.getOption("pointSize", "C"));
  assertEquals(6, g.getOption("pointSize", "D"));
  assertEquals(7, g.getOption("pointSize", "E"));
};

// TODO(konigsberg): move to multiple_axes.js
perSeriesTestCase.prototype.testOldAxisSpecInNewSeriesThrows = function() {
  var opts = {
    series : {
      D : { axis : {} },
    },
  };
  var graph = document.getElementById("graph");
  var data = "X,A,B,C,D,E\n0,1,2,3,4,5\n";
  var threw = false;
  try {
    new Dygraph(graph, data, opts);
  } catch(e) {
    threw = true;
  }

  assertTrue(threw);
}

perSeriesTestCase.prototype.testColorOption = function() {
  var graph = document.getElementById("graph");
  var data = "X,A,B,C\n0,1,2,3\n";
  var g = new Dygraph(graph, data, {});
  assertEquals(['rgb(64,128,0)', 'rgb(64,0,128)', 'rgb(0,128,128)'], g.getColors());
  g.updateOptions({series : { B : { color : 'purple' }}});
  assertEquals(['rgb(64,128,0)', 'purple', 'rgb(0,128,128)'], g.getColors());
}
