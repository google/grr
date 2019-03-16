/**
 * @fileoverview Test cases for how axis labels are chosen and formatted,
 * specializing on the deprecated xLabelFormatter, etc.
 *
 * @author dan@dygraphs.com (Dan Vanderkam)
 */
var DeprecatedAxisLabelsTestCase = TestCase("axis-labels-deprecated");

DeprecatedAxisLabelsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

DeprecatedAxisLabelsTestCase.prototype.tearDown = function() {
};

DeprecatedAxisLabelsTestCase.prototype.testDeprecatedDeprecatedXAxisTimeLabelFormatter = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = [[5.0,0],[5.1,1],[5.2,2],[5.3,3],[5.4,4],[5.5,5],[5.6,6],[5.7,7],[5.8,8],[5.9,9]];
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  g.updateOptions({
    xAxisLabelFormatter: function (totalMinutes) {
      var hours   = Math.floor( totalMinutes / 60);
      var minutes = Math.floor((totalMinutes - (hours * 60)));
      var seconds = Math.round((totalMinutes * 60) - (hours * 3600) - (minutes * 60));

      if (hours   < 10) hours   = "0" + hours;
      if (minutes < 10) minutes = "0" + minutes;
      if (seconds < 10) seconds = "0" + seconds;

      return hours + ':' + minutes + ':' + seconds;
    }
  });

  assertEquals(["00:05:00","00:05:12","00:05:24","00:05:36","00:05:48"], Util.getXLabels());

  // The legend does not use the xAxisLabelFormatter:
  g.setSelection(1);
  assertEquals('5.1: Y1: 1', Util.getLegend());
};

DeprecatedAxisLabelsTestCase.prototype.testDeprecatedAxisLabelFormatter = function () {
  var opts = {
    width: 480,
    height: 320,
    xAxisLabelFormatter: function(x, granularity, opts, dg) {
      assertEquals('number', typeof(x));
      assertEquals('number', typeof(granularity));
      assertEquals('function', typeof(opts));
      assertEquals('[Dygraph graph]', dg.toString());
      return 'x' + x;
    },
    yAxisLabelFormatter: function(y, granularity, opts, dg) {
      assertEquals('number', typeof(y));
      assertEquals('number', typeof(granularity));
      assertEquals('function', typeof(opts));
      assertEquals('[Dygraph graph]', dg.toString());
      return 'y' + y;
    },
    labels: ['x', 'y']
  };
  var data = [];
  for (var i = 0; i < 10; i++) {
    data.push([i, 2 * i]);
  }
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  assertEquals(['x0','x2','x4','x6','x8'], Util.getXLabels());
  assertEquals(["y0","y5","y10","y15"], Util.getYLabels());

  g.setSelection(2);
  assertEquals("2: y: 4", Util.getLegend());
};

DeprecatedAxisLabelsTestCase.prototype.testDeprecatedDateAxisLabelFormatter = function () {
  var opts = {
    width: 480,
    height: 320,
    xAxisLabelFormatter: function(x, granularity, opts, dg) {
      assertTrue(Dygraph.isDateLike(x));
      assertEquals('number', typeof(granularity));
      assertEquals('function', typeof(opts));
      assertEquals('[Dygraph graph]', dg.toString());
      return 'x' + Util.formatDate(x);
    },
    yAxisLabelFormatter: function(y, granularity, opts, dg) {
      assertEquals('number', typeof(y));
      assertEquals('number', typeof(granularity));
      assertEquals('function', typeof(opts));
      assertEquals('[Dygraph graph]', dg.toString());
      return 'y' + y;
    },
    axes: {
      x: { pixelsPerLabel: 60 }
    },
    labels: ['x', 'y']
  };
  var data = [];
  for (var i = 1; i < 10; i++) {
    data.push([new Date("2011/01/0" + i), 2 * i]);
  }
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  assertEquals(["x2011/01/02","x2011/01/04","x2011/01/06","x2011/01/08"], Util.getXLabels());
  assertEquals(["y5","y10","y15"], Util.getYLabels());

  g.setSelection(0);
  assertEquals("2011/01/01: y: 2", Util.getLegend());
};

// This test verifies that when a valueFormatter is set (but not an
// axisLabelFormatter), then the valueFormatter is used to format the axis
// labels.
DeprecatedAxisLabelsTestCase.prototype.testDeprecatedValueFormatter = function () {
  var opts = {
    width: 480,
    height: 320,
    xValueFormatter: function(x, opts, series_name, dg) {
      assertEquals('number', typeof(x));
      assertEquals('function', typeof(opts));
      assertEquals('string', typeof(series_name));
      assertEquals('[Dygraph graph]', dg.toString());
      return 'x' + x;
    },
    yValueFormatter: function(y, opts, series_name, dg) {
      assertEquals('number', typeof(y));
      assertEquals('function', typeof(opts));
      assertEquals('string', typeof(series_name));
      assertEquals('[Dygraph graph]', dg.toString());
      return 'y' + y;
    },
    labels: ['x', 'y']
  };
  var data = [];
  for (var i = 0; i < 10; i++) {
    data.push([i, 2 * i]);
  }
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  // the valueFormatter options do not affect the ticks.
  assertEquals(['0','2','4','6','8'], Util.getXLabels());
  assertEquals(["0","5","10","15"], Util.getYLabels());

  // they do affect the legend, however.
  g.setSelection(2);
  assertEquals("x2: y: y4", Util.getLegend());
};

DeprecatedAxisLabelsTestCase.prototype.testDeprecatedDateValueFormatter = function () {
  var opts = {
    width: 480,
    height: 320,
    xValueFormatter: function(x, opts, series_name, dg) {
      assertEquals('number', typeof(x));
      assertEquals('function', typeof(opts));
      assertEquals('string', typeof(series_name));
      assertEquals('[Dygraph graph]', dg.toString());
      return 'x' + Util.formatDate(x);
    },
    yValueFormatter: function(y, opts, series_name, dg) {
      assertEquals('number', typeof(y));
      assertEquals('function', typeof(opts));
      assertEquals('string', typeof(series_name));
      assertEquals('[Dygraph graph]', dg.toString());
      return 'y' + y;
    },
    axes: { x: { pixelsPerLabel: 60 } },
    labels: ['x', 'y']
  };

  var data = [];
  for (var i = 1; i < 10; i++) {
    data.push([new Date("2011/01/0" + i), 2 * i]);
  }
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  // valueFormatters do not affect ticks.
  assertEquals(["02 Jan","04 Jan","06 Jan","08 Jan"], Util.getXLabels());
  assertEquals(["5","10","15"], Util.getYLabels());

  // the valueFormatter options also affect the legend.
  g.setSelection(2);
  assertEquals('x2011/01/03: y: y6', Util.getLegend());
};

// This test verifies that when both a valueFormatter and an axisLabelFormatter
// are specified, the axisLabelFormatter takes precedence.
DeprecatedAxisLabelsTestCase.prototype.testDeprecatedAxisLabelFormatterPrecedence = function () {
  var opts = {
    width: 480,
    height: 320,
    xValueFormatter: function(x) {
      return 'xvf' + x;
    },
    yValueFormatter: function(y) {
      return 'yvf' + y;
    },
    xAxisLabelFormatter: function(x, granularity) {
      return 'x' + x;
    },
    yAxisLabelFormatter: function(y) {
      return 'y' + y;
    },
    labels: ['x', 'y']
  };
  var data = [];
  for (var i = 0; i < 10; i++) {
    data.push([i, 2 * i]);
  }
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  assertEquals(['x0','x2','x4','x6','x8'], Util.getXLabels());
  assertEquals(["y0","y5","y10","y15"], Util.getYLabels());

  g.setSelection(9);
  assertEquals("xvf9: y: yvf18", Util.getLegend());
};

// This is the same as the previous test, except that options are added
// one-by-one.
DeprecatedAxisLabelsTestCase.prototype.testDeprecatedAxisLabelFormatterIncremental = function () {
  var opts = {
    width: 480,
    height: 320,
    labels: ['x', 'y']
  };
  var data = [];
  for (var i = 0; i < 10; i++) {
    data.push([i, 2 * i]);
  }
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  g.updateOptions({
    xValueFormatter: function(x) {
      return 'xvf' + x;
    }
  });
  g.updateOptions({
    yValueFormatter: function(y) {
      return 'yvf' + y;
    }
  });
  g.updateOptions({
    xAxisLabelFormatter: function(x, granularity) {
      return 'x' + x;
    }
  });
  g.updateOptions({
    yAxisLabelFormatter: function(y) {
      return 'y' + y;
    }
  });

  assertEquals(["x0","x2","x4","x6","x8"], Util.getXLabels());
  assertEquals(["y0","y5","y10","y15"], Util.getYLabels());

  g.setSelection(9);
  assertEquals("xvf9: y: yvf18", Util.getLegend());
};
