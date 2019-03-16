/**
 * @fileoverview Tests zero and one-point charts.
 * These don't have to render nicely, they just have to not crash.
 *
 * @author dan@dygraphs.com (Dan Vanderkam)
 */
var pathologicalCasesTestCase = TestCase("pathological-cases");

pathologicalCasesTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

pathologicalCasesTestCase.prototype.tearDown = function() {
};

pathologicalCasesTestCase.prototype.testZeroPoint = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,Y\n";

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
};

pathologicalCasesTestCase.prototype.testOnePoint = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,Y\n" +
             "1,2\n";

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
};

pathologicalCasesTestCase.prototype.testCombinations = function() {
  var dataSets = {
    empty: [],
    onePoint: [[10, 2]],
    nanPoint: [[10, NaN]],
    nanPoints: [[10, NaN], [20, NaN]],
    multiNan1: [[10, NaN, 2], [20, 3, NaN]],
    multiNan2: [[10, NaN, 2], [20, NaN, 4]],
    multiNan3: [[10, NaN, NaN], [20, 3, 4], [30, NaN, NaN]],
    atZero: [[0, 0]],
    atZero2: [[0, 0, 0]],
    negative: [[-10, -1]],
    acrossZero: [[-10, 1], [10, 2]],
    normal: [[0,1,9], [10,3,5], [20,2,7], [30,4,3]]
  };

  var baseOpts = {
    lines: {},
    stacked: {
      stackedGraph: true
    }
  };

  var variantOpts = {
    none: {},
    avoidMinZero: {
      avoidMinZero: true,
      includeZero: true
    },
    padded: {
      includeZero: true,
      drawAxesAtZero: true,
      xRangePad: 2,
      yRangePad: 4
    }
  };

  for (var baseName in baseOpts) {
    var base = baseOpts[baseName];
    for (var variantName in variantOpts) {
      var variant = variantOpts[variantName];

      var opts = {
        width: 300,
        height: 150,
        labelsDivWidth: 100,
        pointSize: 10
      };
      for (var key in base) {
        if (base.hasOwnProperty(key)) opts[key] = base[key];
      }
      for (var key in variant) {
        if (variant.hasOwnProperty(key)) opts[key] = variant[key];
      }

      var h = document.createElement('h3');
      h.appendChild(document.createTextNode(baseName + ' ' + variantName));
      document.body.appendChild(h);
      for (var dataName in dataSets) {
        var data = dataSets[dataName];

        var box = document.createElement('fieldset');
        box.style.display = 'inline-block';
        var legend = document.createElement('legend');
        legend.appendChild(document.createTextNode(dataName));
        box.appendChild(legend);
        var gdiv = document.createElement('div');
        gdiv.style.display = 'inline-block';
        box.appendChild(gdiv);
        document.body.appendChild(box);

        var cols = data && data[0] ? data[0].length : 0;
        opts.labels = ['X', 'A', 'B', 'C'].slice(0, cols);

        var g = new Dygraph(gdiv, data, opts);
      }
    }
  }
};

pathologicalCasesTestCase.prototype.testNullLegend = function() {
  var opts = {
    width: 480,
    height: 320,
    labelsDiv: null
  };
  var data = "X,Y\n" +
             "1,2\n";

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
};

pathologicalCasesTestCase.prototype.testDivAsString = function() {
  var data = "X,Y\n" +
             "1,2\n";

  var g = new Dygraph('graph', data, {});
};


pathologicalCasesTestCase.prototype.testConstantSeriesNegative = function() {
  var data = "X,Y\n" +
             "1,-1\n" +
             "2,-1\n";

  g = new Dygraph('graph', data, {});
  // This check could be loosened to
  // g.yAxisRange()[0] < g.yAxisRange()[1] if it breaks in the future.
  assertEquals([-1.1, -0.9], g.yAxisRange());
};


pathologicalCasesTestCase.prototype.testConstantSeriesNegativeIncludeZero = function() {
  var data = "X,Y\n" +
             "1,-1\n" +
             "2,-1\n";

  g = new Dygraph('graph', data, {includeZero: true});
  // This check could be loosened to
  // g.yAxisRange()[0] < g.yAxisRange()[1] if it breaks in the future.
  assertEquals([-1.1, 0], g.yAxisRange());
};
