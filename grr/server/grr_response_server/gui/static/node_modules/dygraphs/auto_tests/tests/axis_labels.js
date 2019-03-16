/**
 * @fileoverview Test cases for how axis labels are chosen and formatted.
 *
 * @author dan@dygraphs.com (Dan Vanderkam)
 */
var AxisLabelsTestCase = TestCase("axis-labels");

AxisLabelsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

AxisLabelsTestCase.prototype.tearDown = function() {
};

AxisLabelsTestCase.simpleData =
    "X,Y,Y2\n" +
    "0,-1,.5\n" +
    "1,0,.7\n" +
    "2,1,.4\n" +
    "3,0,.98\n";

AxisLabelsTestCase.prototype.kCloseFloat = 1.0e-10;

AxisLabelsTestCase.prototype.testMinusOneToOne = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  // TODO(danvk): would ['-1.0','-0.5','0.0','0.5','1.0'] be better?
  assertEquals(['-1','-0.5','0','0.5','1'], Util.getYLabels());

  // Go up to 2
  data += "4,2\n";
  g.updateOptions({file: data});
  assertEquals(['-1','-0.5','0','0.5','1','1.5','2'], Util.getYLabels());

  // Now 10
  data += "5,10\n";
  g.updateOptions({file: data});
  assertEquals(['-2','0','2','4','6','8','10'], Util.getYLabels());

  // Now 100
  data += "6,100\n";
  g.updateOptions({file: data});
  assertEquals(['0','20','40','60','80','100'], Util.getYLabels());

  g.setSelection(0);
  assertEquals('0: Y: -1', Util.getLegend());
};

AxisLabelsTestCase.prototype.testSmallRangeNearZero = function() {
  var opts = {
    drawAxesAtZero: true,
    width: 480,
    height: 320
  };
  var data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;
  opts.valueRange = [-0.1, 0.1];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  assertEqualsDelta([-0.1,-0.05,0,0.05],
                    Util.makeNumbers(Util.getYLabels()), this.kCloseFloat);

  opts.valueRange = [-0.05, 0.05];
  g.updateOptions(opts);
  assertEquals([-0.04,-0.02,0,0.02,0.04],
               Util.makeNumbers(Util.getYLabels()));

  opts.valueRange = [-0.01, 0.01];
  g.updateOptions(opts);
  assertEquals([-0.01,-0.005,0,0.005],
               Util.makeNumbers(Util.getYLabels()));

  g.setSelection(1);
  assertEquals('1: Y: 0', Util.getLegend());
};

AxisLabelsTestCase.prototype.testSmallRangeAwayFromZero = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;
  var graph = document.getElementById("graph");

  opts.valueRange = [9.9, 10.1];
  var g = new Dygraph(graph, data, opts);
  assertEquals(["9.9","9.92","9.94","9.96","9.98","10","10.02","10.04","10.06","10.08"], Util.getYLabels());

  opts.valueRange = [9.99, 10.01];
  g.updateOptions(opts);
  // TODO(danvk): this is bad
  assertEquals(["9.99","9.99","9.99","10","10","10","10","10","10.01","10.01"], Util.getYLabels());

  opts.valueRange = [9.999, 10.001];
  g.updateOptions(opts);
  // TODO(danvk): this is even worse!
  assertEquals(["10","10","10","10"], Util.getYLabels());

  g.setSelection(1);
  assertEquals('1: Y: 0', Util.getLegend());
};

AxisLabelsTestCase.prototype.testXAxisTimeLabelFormatter = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = [[5.0,0],[5.1,1],[5.2,2],[5.3,3],[5.4,4],[5.5,5],[5.6,6],[5.7,7],[5.8,8],[5.9,9]];
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  g.updateOptions({
    axes : {
      x : {
        axisLabelFormatter : function (totalMinutes) {
          var hours   = Math.floor( totalMinutes / 60);
          var minutes = Math.floor((totalMinutes - (hours * 60)));
          var seconds = Math.round((totalMinutes * 60) - (hours * 3600) - (minutes * 60));

          if (hours   < 10) hours   = "0" + hours;
          if (minutes < 10) minutes = "0" + minutes;
          if (seconds < 10) seconds = "0" + seconds;

          return hours + ':' + minutes + ':' + seconds;
        }
      }
    }
  });

  assertEquals(["00:05:00","00:05:12","00:05:24","00:05:36","00:05:48"], Util.getXLabels());

  // The legend does not use the axisLabelFormatter:
  g.setSelection(1);
  assertEquals('5.1: Y1: 1', Util.getLegend());
};

AxisLabelsTestCase.prototype.testAxisLabelFormatter = function () {
  var opts = {
    width: 480,
    height: 320,
    axes : {
      x : {
        axisLabelFormatter : function(x, granularity, opts, dg) {
          assertEquals('number', typeof(x));
          assertEquals('number', typeof(granularity));
          assertEquals('function', typeof(opts));
          assertEquals('[Dygraph graph]', dg.toString());
          return 'x' + x;
        }
      },
      y : {
        axisLabelFormatter : function(y, granularity, opts, dg) {
          assertEquals('number', typeof(y));
          assertEquals('number', typeof(granularity));
          assertEquals('function', typeof(opts));
          assertEquals('[Dygraph graph]', dg.toString());
          return 'y' + y;
        }
      }
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

AxisLabelsTestCase.prototype.testDateAxisLabelFormatter = function () {
  var opts = {
    width: 480,
    height: 320,
    axes : {
      x : {
        pixelsPerLabel: 60,
        axisLabelFormatter : function(x, granularity, opts, dg) {
          assertTrue(Dygraph.isDateLike(x));
          assertEquals('number', typeof(granularity));
          assertEquals('function', typeof(opts));
          assertEquals('[Dygraph graph]', dg.toString());
          return 'x' + Util.formatDate(x);
        }
      },
      y : {
        axisLabelFormatter : function(y, granularity, opts, dg) {
          assertEquals('number', typeof(y));
          assertEquals('number', typeof(granularity));
          assertEquals('function', typeof(opts));
          assertEquals('[Dygraph graph]', dg.toString());
          return 'y' + y;
        }
      }
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
AxisLabelsTestCase.prototype.testValueFormatter = function () {
  var opts = {
    width: 480,
    height: 320,
    axes: {
      x: {
        valueFormatter: function(x, opts, series_name, dg, row, col) {
          assertEquals('number', typeof(x));
          assertEquals('function', typeof(opts));
          assertEquals('string', typeof(series_name));
          assertEquals('[Dygraph graph]', dg.toString());
          assertEquals('number', typeof(row));
          assertEquals('number', typeof(col));
          assertEquals(dg, this);
          return 'x' + x;
        }
      },
      y: {
        valueFormatter: function(y, opts, series_name, dg, row, col) {
          assertEquals('number', typeof(y));
          assertEquals('function', typeof(opts));
          assertEquals('string', typeof(series_name));
          assertEquals('[Dygraph graph]', dg.toString());
          assertEquals('number', typeof(row));
          assertEquals('number', typeof(col));
          assertEquals(dg, this);
          return 'y' + y;
        }
      }
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
  assertEquals(["0","5","10","15"],
               Util.getYLabels());

  // they do affect the legend, however.
  g.setSelection(2);
  assertEquals("x2: y: y4", Util.getLegend());
};

AxisLabelsTestCase.prototype.testDateValueFormatter = function () {
  var opts = {
    width: 480,
    height: 320,
    axes : {
      x : {
        pixelsPerLabel: 60,
        valueFormatter: function(x, opts, series_name, dg, row, col) {
          assertEquals('number', typeof(x));
          assertEquals('function', typeof(opts));
          assertEquals('string', typeof(series_name));
          assertEquals('[Dygraph graph]', dg.toString());
          assertEquals('number', typeof(row));
          assertEquals('number', typeof(col));
          assertEquals(dg, this);
          return 'x' + Util.formatDate(x);
        }
      },
      y : {
        valueFormatter: function(y, opts, series_name, dg, row, col) {
          assertEquals('number', typeof(y));
          assertEquals('function', typeof(opts));
          assertEquals('string', typeof(series_name));
          assertEquals('[Dygraph graph]', dg.toString());
          assertEquals('number', typeof(row));
          assertEquals('number', typeof(col));
          assertEquals(dg, this);
          return 'y' + y;
        }
      }
    },
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
AxisLabelsTestCase.prototype.testAxisLabelFormatterPrecedence = function () {
  var opts = {
    width: 480,
    height: 320,
    axes : {
      x : {
        valueFormatter: function(x) {
          assertEquals('[Dygraph graph]', this.toString());
          return 'xvf' + x;
        },
        axisLabelFormatter: function(x, granularity) {
          assertEquals('[Dygraph graph]', this.toString());
          return 'x' + x;
        }
      },
      y : {
        valueFormatter: function(y) {
          assertEquals('[Dygraph graph]', this.toString());
          return 'yvf' + y;
        },
        axisLabelFormatter: function(y) {
          assertEquals('[Dygraph graph]', this.toString());
          return 'y' + y;
        }
      }
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
AxisLabelsTestCase.prototype.testAxisLabelFormatterIncremental = function () {
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
    axes : {
      x : {
        valueFormatter: function(x) {
          return 'xvf' + x;
        }
      }
    }
  });
  g.updateOptions({
    axes : {
      y : {
        valueFormatter: function(y) {
          return 'yvf' + y;
        }
      }
    }
  });
  g.updateOptions({
    axes : {
      x : {
        axisLabelFormatter: function(x, granularity) {
          return 'x' + x;
        }
      }
    }
  });
  g.updateOptions({
    axes : {
      y : {
        axisLabelFormatter: function(y) {
          return 'y' + y;
        }
      }
    }
  });

  assertEquals(["x0","x2","x4","x6","x8"], Util.getXLabels());
  assertEquals(["y0","y5","y10","y15"], Util.getYLabels());

  g.setSelection(9);
  assertEquals("xvf9: y: yvf18", Util.getLegend());
};

AxisLabelsTestCase.prototype.testGlobalFormatters = function() {
  var opts = {
    width: 480,
    height: 320,
    labels: ['x', 'y'],
    valueFormatter: function(x) {
      assertEquals('[Dygraph graph]', this);
      return 'vf' + x;
    },
    axisLabelFormatter: function(x) {
      assertEquals('[Dygraph graph]', this);
      return 'alf' + x;
    }
  };
  var data = [];
  for (var i = 0; i < 10; i++) {
    data.push([i, 2 * i]);
  }
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  assertEquals(['alf0','alf2','alf4','alf6','alf8'], Util.getXLabels());
  assertEquals(["alf0","alf5","alf10","alf15"], Util.getYLabels());

  g.setSelection(9);
  assertEquals("vf9: y: vf18", Util.getLegend());
};

AxisLabelsTestCase.prototype.testValueFormatterParameters = function() {
  var calls = [];
  // change any functions in list to 'fn' -- functions can't be asserted.
  var killFunctions = function(list) {
    var out = [];
    for (var i = 0; i < list.length; i++) {
      if (typeof(list[i]) == 'function') {
        out[i] = 'fn';
      } else {
        out[i] = list[i];
      }
    }
    return out;
  };
  var taggedRecorder = function(tag) {
    return function() {
      calls.push([tag].concat([this], killFunctions(arguments)));
      return '';
    }
  };
  var opts = {
    axes: {
      x:  { valueFormatter: taggedRecorder('x') },
      y:  { valueFormatter: taggedRecorder('y') },
      y2: { valueFormatter: taggedRecorder('y2') }
    },
    series: {
      'y1': { axis: 'y1'},
      'y2': { axis: 'y2'}
    },
    labels: ['x', 'y1', 'y2']
  };
  var data = [
    [0, 1, 2],
    [1, 3, 4]
  ];
  var graph = document.getElementById('graph');
  var g = new Dygraph(graph, data, opts);

  assertEquals([], calls);
  g.setSelection(0);
  assertEquals([
    // num or millis, opts, series, dygraph, row, col
    [ 'x', g, 0, 'fn',  'x', g, 0, 0],
    [ 'y', g, 1, 'fn', 'y1', g, 0, 1],
    ['y2', g, 2, 'fn', 'y2', g, 0, 2]
  ], calls);

  calls = [];
  g.setSelection(1);
  assertEquals([
    [ 'x', g, 1, 'fn',  'x', g, 1, 0],
    [ 'y', g, 3, 'fn', 'y1', g, 1, 1],
    ['y2', g, 4, 'fn', 'y2', g, 1, 2]
  ], calls);
};

AxisLabelsTestCase.prototype.testSeriesOrder = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "x,00,01,10,11\n" +
      "0,101,201,301,401\n" +
      "1,102,202,302,402\n" +
      "2,103,203,303,403\n" +
      "3,104,204,304,404\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  g.setSelection(2);
  assertEquals('2: 00: 103 01: 203 10: 303 11: 403', Util.getLegend());

  // Sanity checks for indexFromSetName
  assertEquals(0, g.indexFromSetName("x"));
  assertEquals(1, g.indexFromSetName("00"));
  assertEquals(null, g.indexFromSetName("abcde"));

  // Verify that we get the label list back in the right order
  assertEquals(["x", "00", "01", "10", "11"], g.getLabels());
};

AxisLabelsTestCase.prototype.testLabelKMB = function() {
  var data = [];
  data.push([0,0]);
  data.push([1,2000]);
  data.push([2,1000]);

  var g = new Dygraph(
    document.getElementById("graph"),
    data,
    {
      labels: [ 'X', 'bar' ],
      axes : {
        y: {
          labelsKMB: true
        }
      }
    }
  );

  assertEquals(["0", "500", "1K", "1.5K", "2K"], Util.getYLabels());
};

AxisLabelsTestCase.prototype.testLabelKMG2 = function() {
  var data = [];
  data.push([0,0]);
  data.push([1,2000]);
  data.push([2,1000]);

  var g = new Dygraph(
    document.getElementById("graph"),
    data,
    {
      labels: [ 'X', 'bar' ],
      axes : {
        y: {
          labelsKMG2: true
        }
      }
    }
  );

  assertEquals(
      ["0","256","512","768","1k","1.25k","1.5k","1.75k","2k"],
      Util.getYLabels());
};

// Same as testLabelKMG2 but specifies the option at the
// top of the option dictionary.
AxisLabelsTestCase.prototype.testLabelKMG2_top = function() {
  var data = [];
  data.push([0,0]);
  data.push([1,2000]);
  data.push([2,1000]);

  var g = new Dygraph(
    document.getElementById("graph"),
    data,
    {
      labels: [ 'X', 'bar' ],
      labelsKMG2: true
    }
  );

  assertEquals(
      ["0","256","512","768","1k","1.25k","1.5k","1.75k","2k"],
      Util.getYLabels());
};

/**
 * Verify that log scale axis range is properly specified.
 */
AxisLabelsTestCase.prototype.testLogScale = function() {
  var g = new Dygraph("graph", [[0, 5], [1, 1000]], { logscale : true });
  var nonEmptyLabels = Util.getYLabels().filter(function(x) { return x.length > 0; });
  assertEquals(["5","10","20","50","100","200","500","1000"], nonEmptyLabels);
 
  g.updateOptions({ logscale : false });
  assertEquals(['0','200','400','600','800','1000'], Util.getYLabels());
}

/**
 * Verify that include zero range is properly specified.
 */
AxisLabelsTestCase.prototype.testIncludeZero = function() {
  var g = new Dygraph("graph", [[0, 500], [1, 1000]], { includeZero : true });
  assertEquals(['0','200','400','600','800','1000'], Util.getYLabels());
 
  g.updateOptions({ includeZero : false });
  assertEquals(['500','600','700','800','900','1000'], Util.getYLabels());
}

AxisLabelsTestCase.prototype.testAxisLabelFontSize = function() {
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, AxisLabelsTestCase.simpleData, {});

  // Be sure we're dealing with a 14-point default.
  assertEquals(14, Dygraph.DEFAULT_ATTRS.axisLabelFontSize);

  var assertFontSize = function(selector, expected) {
    Util.assertStyleOfChildren(selector, "font-size", expected);
  }
  
  assertFontSize($(".dygraph-axis-label-x"), "14px");
  assertFontSize($(".dygraph-axis-label-y") , "14px");

  g.updateOptions({ axisLabelFontSize : 8});
  assertFontSize($(".dygraph-axis-label-x"), "8px"); 
  assertFontSize($(".dygraph-axis-label-y"), "8px"); 

  g.updateOptions({
    axisLabelFontSize : null,
    axes : { 
      x : { axisLabelFontSize : 5 },
    }   
  }); 

  assertFontSize($(".dygraph-axis-label-x"), "5px"); 
  assertFontSize($(".dygraph-axis-label-y"), "14px");

  g.updateOptions({
    axes : { 
      y : { axisLabelFontSize : 20 },
    }   
  }); 

  assertFontSize($(".dygraph-axis-label-x"), "5px"); 
  assertFontSize($(".dygraph-axis-label-y"), "20px"); 

  g.updateOptions({
    series : { 
      Y2 : { axis : "y2" } // copy y2 series to y2 axis.
    },  
    axes : { 
      y2 : { axisLabelFontSize : 12 },
    }   
  }); 

  assertFontSize($(".dygraph-axis-label-x"), "5px"); 
  assertFontSize($(".dygraph-axis-label-y1"), "20px"); 
  assertFontSize($(".dygraph-axis-label-y2"), "12px"); 
}

AxisLabelsTestCase.prototype.testAxisLabelFontSizeNull = function() {
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, AxisLabelsTestCase.simpleData,
    {
      axisLabelFontSize: null
    });

  var assertFontSize = function(selector, expected) {
    Util.assertStyleOfChildren(selector, "font-size", expected);
  };

  // Be sure we're dealing with a 14-point default.
  assertEquals(14, Dygraph.DEFAULT_ATTRS.axisLabelFontSize);

  assertFontSize($(".dygraph-axis-label-x"), "14px");
  assertFontSize($(".dygraph-axis-label-y"), "14px");
}

AxisLabelsTestCase.prototype.testAxisLabelColor = function() {
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, AxisLabelsTestCase.simpleData, {});

  // Be sure we're dealing with a black default.
  assertEquals("black", Dygraph.DEFAULT_ATTRS.axisLabelColor);

  var assertColor = function(selector, expected) {
    Util.assertStyleOfChildren(selector, "color", expected);
  }

  assertColor($(".dygraph-axis-label-x"), "rgb(0, 0, 0)");
  assertColor($(".dygraph-axis-label-y"), "rgb(0, 0, 0)");

  g.updateOptions({ axisLabelColor : "red"});
  assertColor($(".dygraph-axis-label-x"), "rgb(255, 0, 0)"); 
  assertColor($(".dygraph-axis-label-y"), "rgb(255, 0, 0)"); 

  g.updateOptions({
    axisLabelColor : null,
    axes : { 
      x : { axisLabelColor : "blue" },
    }   
  }); 

  assertColor($(".dygraph-axis-label-x"), "rgb(0, 0, 255)"); 
  assertColor($(".dygraph-axis-label-y"), "rgb(0, 0, 0)");

  g.updateOptions({
    axes : { 
      y : { axisLabelColor : "green" },
    }   
  }); 

  assertColor($(".dygraph-axis-label-x"), "rgb(0, 0, 255)"); 
  assertColor($(".dygraph-axis-label-y"), "rgb(0, 128, 0)"); 

  g.updateOptions({
    series : { 
      Y2 : { axis : "y2" } // copy y2 series to y2 axis.
    },  
    axes : { 
      y2 : { axisLabelColor : "yellow" },
    }   
  }); 

  assertColor($(".dygraph-axis-label-x"), "rgb(0, 0, 255)"); 
  assertColor($(".dygraph-axis-label-y1"), "rgb(0, 128, 0)"); 
  assertColor($(".dygraph-axis-label-y2"), "rgb(255, 255, 0)"); 
}

AxisLabelsTestCase.prototype.testAxisLabelColorNull = function() {
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, AxisLabelsTestCase.simpleData,
    {
      axisLabelColor: null
    });

  var assertColor = function(selector, expected) {
    Util.assertStyleOfChildren(selector, "color", expected);
  }

  // Be sure we're dealing with a 14-point default.
  assertEquals(14, Dygraph.DEFAULT_ATTRS.axisLabelFontSize);

  assertColor($(".dygraph-axis-label-x"), "rgb(0, 0, 0)");
  assertColor($(".dygraph-axis-label-y"), "rgb(0, 0, 0)");
}

/*
 * This test shows that the label formatter overrides labelsKMB for all values.
 */
AxisLabelsTestCase.prototype.testLabelFormatterOverridesLabelsKMB = function() {
  var g = new Dygraph(
      document.getElementById("graph"),
      "X,a,b\n" +
      "1,0,2000\n" +
      "2,500,1500\n" +
      "3,1000,1000\n" +
      "4,2000,0\n", {
        labelsKMB: true,
        axisLabelFormatter: function (v) {
          return v + ":X";
        }
      });
  assertEquals(["0:X","500:X","1000:X","1500:X","2000:X"], Util.getYLabels());
  assertEquals(["1:X","2:X","3:X"], Util.getXLabels());
}

/*
 * This test shows that you can override labelsKMB on the axis level.
 */
AxisLabelsTestCase.prototype.testLabelsKMBPerAxis = function() {
  var g = new Dygraph(
      document.getElementById("graph"),
      "x,a,b\n" +
      "1000,0,2000\n" +
      "2000,500,1500\n" +
      "3000,1000,1000\n" +
      "4000,2000,0\n", {
        labelsKMB: false,
        axes: {
          y2: { labelsKMB: true },
          x: { labelsKMB: true }
        },
        series: {
          b: { axis: "y2" }
        }
      });

  // labelsKMB doesn't apply to the x axis. This value should be different.
  // BUG : https://code.google.com/p/dygraphs/issues/detail?id=488
  assertEquals(["1000","2000","3000"], Util.getXLabels());
  assertEquals( ["0","500","1000","1500","2000"], Util.getYLabels(1));
  assertEquals(["0","500","1K","1.5K","2K"], Util.getYLabels(2));
};

/*
 * This test shows that you can override labelsKMG2 on the axis level.
 */
AxisLabelsTestCase.prototype.testLabelsKMBG2IPerAxis = function() {
  var g = new Dygraph(
      document.getElementById("graph"),
      "x,a,b\n" +
      "1000,0,2000\n" +
      "2000,500,1500\n" +
      "3000,1000,1000\n" +
      "4000,2000,0\n", {
        labelsKMG2: false,
        axes: {
          y2: { labelsKMG2: true },
          x: { labelsKMG2: true, pixelsPerLabel: 60 }
        },
        series: {
          b: { axis: "y2" }
        }
      });

  // It is weird that labelsKMG2 does something on the x axis but KMB does not.
  // Plus I can't be sure they're doing the same thing as they're done in different
  // bits of code.
  // BUG : https://code.google.com/p/dygraphs/issues/detail?id=488
  assertEquals(["1024","2048","3072"], Util.getXLabels());
  assertEquals( ["0","500","1000","1500","2000"], Util.getYLabels(1));
  assertEquals(["0","500","1000","1.46k","1.95k"], Util.getYLabels(2));
};

/**
 * This test shows you can override sigFigs on the axis level.
 */
AxisLabelsTestCase.prototype.testSigFigsPerAxis = function() {
  var g = new Dygraph(
      document.getElementById("graph"),
      "x,a,b\n" +
      "1000,0,2000\n" +
      "2000,500,1500\n" +
      "3000,1000,1000\n" +
      "4000,2000,0\n", {
        sigFigs: 2,
        axes: {
          y2: { sigFigs: 6 },
          x: { sigFigs: 8 }
        },
        series: {
          b: { axis: "y2" }
        }

      });
  // sigFigs doesn't apply to the x axis. This value should be different.
  // BUG : https://code.google.com/p/dygraphs/issues/detail?id=488
  assertEquals(["1000","2000","3000"], Util.getXLabels());
  assertEquals(["0.0","5.0e+2","1.0e+3","1.5e+3","2.0e+3"], Util.getYLabels(1));
  assertEquals(["0.00000","500.000","1000.00","1500.00","2000.00"], Util.getYLabels(2));
}

/**
 * This test shows you can override digitsAfterDecimal on the axis level.
 */
AxisLabelsTestCase.prototype.testDigitsAfterDecimalPerAxis = function() {
  var g = new Dygraph(
      document.getElementById("graph"),
      "x,a,b\n" +
      "0.006,0.001,0.008\n" +
      "0.007,0.002,0.007\n" +
      "0.008,0.003,0.006\n" +
      "0.009,0.004,0.005\n", {
        digitsAfterDecimal: 1,
        series: {
          b: { axis: "y2" }
        }

      });

  g.updateOptions({ axes: { y: { digitsAfterDecimal: 3 }}});
  assertEquals(["0.001","0.002","0.002","0.003","0.003","0.004","0.004"], Util.getYLabels(1));
  g.updateOptions({ axes: { y: { digitsAfterDecimal: 4 }}});
  assertEquals(["0.001","0.0015","0.002","0.0025","0.003","0.0035","0.004"], Util.getYLabels(1));
  g.updateOptions({ axes: { y: { digitsAfterDecimal: 5 }}});
  assertEquals(["0.001","0.0015","0.002","0.0025","0.003","0.0035","0.004"], Util.getYLabels(1));
  g.updateOptions({ axes: { y: { digitsAfterDecimal: null }}});
  assertEquals(["1e-3","2e-3","2e-3","3e-3","3e-3","4e-3","4e-3"], Util.getYLabels(1));

  g.updateOptions({ axes: { y2: { digitsAfterDecimal: 3 }}});
  assertEquals(["0.005","0.006","0.006","0.007","0.007","0.008","0.008"], Util.getYLabels(2));
  g.updateOptions({ axes: { y2: { digitsAfterDecimal: 4 }}});
  assertEquals(["0.005","0.0055","0.006","0.0065","0.007","0.0075","0.008"], Util.getYLabels(2));
  g.updateOptions({ axes: { y2: { digitsAfterDecimal: 5 }}});
  assertEquals(["0.005","0.0055","0.006","0.0065","0.007","0.0075","0.008"], Util.getYLabels(2));
  g.updateOptions({ axes: { y2: { digitsAfterDecimal: null }}});
  assertEquals(["5e-3","6e-3","6e-3","7e-3","7e-3","7e-3","8e-3"], Util.getYLabels(2));


  // digitsAfterDecimal is ignored for the x-axis.
  // BUG : https://code.google.com/p/dygraphs/issues/detail?id=488
  g.updateOptions({ axes: { x: { digitsAfterDecimal: 3 }}});
  assertEquals(["0.006","0.007","0.008"], Util.getXLabels());
  g.updateOptions({ axes: { x: { digitsAfterDecimal: 4 }}});
  assertEquals(["0.006","0.007","0.008"], Util.getXLabels());
  g.updateOptions({ axes: { x: { digitsAfterDecimal: 5 }}});
  assertEquals(["0.006","0.007","0.008"], Util.getXLabels());
  g.updateOptions({ axes: { x: { digitsAfterDecimal: null }}});
  assertEquals(["0.006","0.007","0.008"], Util.getXLabels());
}

/**
 * This test shows you can override digitsAfterDecimal on the axis level.
 */
AxisLabelsTestCase.prototype.testMaxNumberWidthPerAxis = function() {
  var g = new Dygraph(
      document.getElementById("graph"),
      "x,a,b\n" +
      "12401,12601,12804\n" +
      "12402,12602,12803\n" +
      "12403,12603,12802\n" +
      "12404,12604,12801\n", {
        maxNumberWidth: 1,
        series: {
          b: { axis: "y2" }
        }
      });

  g.updateOptions({ axes: { y: { maxNumberWidth: 4 }}});
  assertEquals(["1.26e+4","1.26e+4","1.26e+4","1.26e+4","1.26e+4","1.26e+4","1.26e+4"] , Util.getYLabels(1));
  g.updateOptions({ axes: { y: { maxNumberWidth: 5 }}});
  assertEquals(["12601","12601.5","12602","12602.5","12603","12603.5","12604"] , Util.getYLabels(1));
  g.updateOptions({ axes: { y: { maxNumberWidth: null }}});
  assertEquals(["1.26e+4","1.26e+4","1.26e+4","1.26e+4","1.26e+4","1.26e+4","1.26e+4"] , Util.getYLabels(1));

  g.updateOptions({ axes: { y2: { maxNumberWidth: 4 }}});
  assertEquals(["1.28e+4","1.28e+4","1.28e+4","1.28e+4","1.28e+4","1.28e+4","1.28e+4"], Util.getYLabels(2));
  g.updateOptions({ axes: { y2: { maxNumberWidth: 5 }}});
  assertEquals(["12801","12801.5","12802","12802.5","12803","12803.5","12804"], Util.getYLabels(2));
  g.updateOptions({ axes: { y2: { maxNumberWidth: null }}});
  assertEquals(["1.28e+4","1.28e+4","1.28e+4","1.28e+4","1.28e+4","1.28e+4","1.28e+4"], Util.getYLabels(2));

  // maxNumberWidth is ignored for the x-axis.
  // BUG : https://code.google.com/p/dygraphs/issues/detail?id=488
  g.updateOptions({ axes: { x: { maxNumberWidth: 4 }}});
  assertEquals(["12401","12402","12403"], Util.getXLabels());
  g.updateOptions({ axes: { x: { maxNumberWidth: 5 }}});
  assertEquals(["12401","12402","12403"], Util.getXLabels());
  g.updateOptions({ axes: { x: { maxNumberWidth: null }}});
  assertEquals(["12401","12402","12403"], Util.getXLabels());
}

/*
// Regression test for http://code.google.com/p/dygraphs/issues/detail?id=147
// Checks that axis labels stay sane across a DST change.
AxisLabelsTestCase.prototype.testLabelsCrossDstChange = function() {
  // (From tests/daylight-savings.html)
  var g = new Dygraph(
      document.getElementById("graph"),
      "Date/Time,Purchases\n" +
      "2010-11-05 00:00:00,167082\n" +
      "2010-11-06 00:00:00,168571\n" +
      "2010-11-07 00:00:00,177796\n" +
      "2010-11-08 00:00:00,165587\n" +
      "2010-11-09 00:00:00,164380\n",
      { width: 1024 }
      );

  // Dates and "nice" hours: 6AM/PM and noon, not 5AM/11AM/...
  var okLabels = {
    '05Nov': true,
    '06Nov': true,
    '07Nov': true,
    '08Nov': true,
    '09Nov': true,
    '06:00': true,
    '12:00': true,
    '18:00': true
  };

  var xLabels = Util.getXLabels();
  for (var i = 0; i < xLabels.length; i++) {
    assertTrue(okLabels[xLabels[i]]);
  }

  // This range had issues of its own on tests/daylight-savings.html.
  g.updateOptions({
    dateWindow: [1289109997722.8127, 1289261208937.7659]
  });
  xLabels = Util.getXLabels();
  for (var i = 0; i < xLabels.length; i++) {
    assertTrue(okLabels[xLabels[i]]);
  }
};


// Tests data which crosses a "fall back" at a high enough frequency that you
// can see both 1:00 A.M.s.
AxisLabelsTestCase.prototype.testLabelsCrossDstChangeHighFreq = function() {
  // Generate data which crosses the EST/EDT boundary.
  var dst_data = [];
  var base_ms = 1383454200000;
  for (var x = base_ms; x < base_ms + 1000 * 60 * 80; x += 1000) {
    dst_data.push([new Date(x), x]);
  }

  var g = new Dygraph(
          document.getElementById("graph"),
          dst_data,
      { width: 1024, labels: ['Date', 'Value'] }
      );

  assertEquals([
    '00:50', '00:55',
    '01:00', '01:05', '01:10', '01:15', '01:20', '01:25',
    '01:30', '01:35', '01:40', '01:45', '01:50', '01:55',
    '01:00', '01:05'  // 1 AM number two!
  ], Util.getXLabels());

  // Now zoom past the initial 1 AM. This used to cause trouble.
  g.updateOptions({
    dateWindow: [1383454200000 + 15*60*1000, g.xAxisExtremes()[1]]}
  );
  assertEquals([
    '01:05', '01:10', '01:15', '01:20', '01:25',
    '01:30', '01:35', '01:40', '01:45', '01:50', '01:55',
    '01:00', '01:05'  // 1 AM number two!
  ], Util.getXLabels());
};


// Tests data which crosses a "spring forward" at a low frequency.
// Regression test for http://code.google.com/p/dygraphs/issues/detail?id=433
AxisLabelsTestCase.prototype.testLabelsCrossSpringForward = function() {
  var g = new Dygraph(
      document.getElementById("graph"),
      "Date/Time,Purchases\n" +
      "2011-03-11 00:00:00,167082\n" +
      "2011-03-12 00:00:00,168571\n" +
      "2011-03-13 00:00:00,177796\n" +
      "2011-03-14 00:00:00,165587\n" +
      "2011-03-15 00:00:00,164380\n",
      {
        width: 1024,
        dateWindow: [1299989043119.4365, 1300080693627.4866]
      });

  var okLabels = {
    '13Mar': true,
    // '02:00': true,  // not a real time!
    '04:00': true,
    '06:00': true,
    '08:00': true,
    '10:00': true,
    '12:00': true,
    '14:00': true,
    '16:00': true,
    '18:00': true,
    '20:00': true,
    '22:00': true,
    '14Mar': true
  };

  var xLabels = Util.getXLabels();
  for (var i = 0; i < xLabels.length; i++) {
    assertTrue(okLabels[xLabels[i]]);
  }
};

AxisLabelsTestCase.prototype.testLabelsCrossSpringForwardHighFreq = function() {
  var base_ms_spring = 1299999000000;
  var dst_data_spring = [];
  for (var x = base_ms_spring; x < base_ms_spring + 1000 * 60 * 80; x += 1000) {
    dst_data_spring.push([new Date(x), x]);
  }

  var g = new Dygraph(
      document.getElementById("graph"),
      dst_data_spring,
      { width: 1024, labels: ['Date', 'Value'] }
  );

  assertEquals([
    '01:50', '01:55',
    '03:00', '03:05', '03:10', '03:15', '03:20', '03:25',
    '03:30', '03:35', '03:40', '03:45', '03:50', '03:55',
    '04:00', '04:05'
  ], Util.getXLabels());
};
*/
