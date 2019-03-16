/**
 * @fileoverview Tests for rolling averages.
 *
 * @author danvk@google.com (Dan Vanderkam)
 */
var rollingAverageTestCase = TestCase("rolling-average");

rollingAverageTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

rollingAverageTestCase.prototype.tearDown = function() {
};

rollingAverageTestCase.prototype.testRollingAverage = function() {
  var opts = {
    width: 480,
    height: 320,
    rollPeriod: 1,
    showRoller: true
  };
  var data = "X,Y\n" +
      "0,0\n" +
      "1,1\n" +
      "2,2\n" +
      "3,3\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  g.setSelection(0); assertEquals("0: Y: 0", Util.getLegend());
  g.setSelection(1); assertEquals("1: Y: 1", Util.getLegend());
  g.setSelection(2); assertEquals("2: Y: 2", Util.getLegend());
  g.setSelection(3); assertEquals("3: Y: 3", Util.getLegend());
  assertEquals(1, g.rollPeriod());

  g.updateOptions({rollPeriod: 2});
  g.setSelection(0); assertEquals("0: Y: 0", Util.getLegend());
  g.setSelection(1); assertEquals("1: Y: 0.5", Util.getLegend());
  g.setSelection(2); assertEquals("2: Y: 1.5", Util.getLegend());
  g.setSelection(3); assertEquals("3: Y: 2.5", Util.getLegend());
  assertEquals(2, g.rollPeriod());

  g.updateOptions({rollPeriod: 3});
  g.setSelection(0); assertEquals("0: Y: 0", Util.getLegend());
  g.setSelection(1); assertEquals("1: Y: 0.5", Util.getLegend());
  g.setSelection(2); assertEquals("2: Y: 1", Util.getLegend());
  g.setSelection(3); assertEquals("3: Y: 2", Util.getLegend());
  assertEquals(3, g.rollPeriod());

  g.updateOptions({rollPeriod: 4});
  g.setSelection(0); assertEquals("0: Y: 0", Util.getLegend());
  g.setSelection(1); assertEquals("1: Y: 0.5", Util.getLegend());
  g.setSelection(2); assertEquals("2: Y: 1", Util.getLegend());
  g.setSelection(3); assertEquals("3: Y: 1.5", Util.getLegend());
  assertEquals(4, g.rollPeriod());
};

rollingAverageTestCase.prototype.testRollBoxDoesntDisapper = function() {
  var opts = {
    showRoller: true
  };
  var data = "X,Y\n" +
      "0,0\n" +
      "1,1\n" +
      "2,2\n" +
      "3,3\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  var roll_box = graph.getElementsByTagName("input");
  assertEquals(1, roll_box.length);
  assertEquals("1", roll_box[0].value);

  graph.style.width = "500px";
  g.resize();
  assertEquals(1, roll_box.length);
  assertEquals("1", roll_box[0].value);
};

// Regression test for http://code.google.com/p/dygraphs/issues/detail?id=426
rollingAverageTestCase.prototype.testRollShortFractions = function() {
  var opts = {
    customBars: true,
    labels: ['x', 'A']
  };
  var data1 = [ [1, 10, [1, 20]] ];
  var data2 = [ [1, 10, [1, 20]],
                [2, 20, [1, 30]],
              ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data2, opts);

  var rolled1 = g.dataHandler_.rollingAverage(data1, 1, g);
  var rolled2 = g.dataHandler_.rollingAverage(data2, 1, g);

  assertEquals(rolled1[0], rolled2[0]);
};

rollingAverageTestCase.prototype.testRollCustomBars = function() {
  var opts = {
    customBars: true,
    rollPeriod: 2,
    labels: ['x', 'A']
  };
  var data = [ [1, [1, 10, 20]],
               [2, [1, 20, 30]],
               [3, [1, 30, 40]],
               [4, [1, 40, 50]]
              ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  var rolled = this.getRolledData(g, data, 1, 2);
  assertEquals([1, 10, [1, 20]], rolled[0]);
  assertEquals([2, 15, [1, 25]], rolled[1]);
  assertEquals([3, 25, [1, 35]], rolled[2]);
  assertEquals([4, 35, [1, 45]], rolled[3]);
};

rollingAverageTestCase.prototype.testRollErrorBars = function() {
  var opts = {
    errorBars: true,
    rollPeriod: 2,
    labels: ['x', 'A']
  };
  var data = [ [1, [10, 1]],
               [2, [20, 1]],
               [3, [30, 1]],
               [4, [40, 1]]
              ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  var rolled = this.getRolledData(g, data, 1, 2);
  assertEquals([1, 10, [8, 12]], rolled[0]);
 
  // variance = sqrt( pow(error) * rollPeriod)
  var variance = Math.sqrt(2);
  for (var i=1;i<data.length;i++) {
    var value = data[i][1][0] - 5;
    assertEquals("unexpected rolled average", value, rolled[i][1]);
    assertEquals("unexpected rolled min", value - variance, rolled[i][2][0]);
    assertEquals("unexpected rolled max", value + variance, rolled[i][2][1]);
  }
};

rollingAverageTestCase.prototype.testRollFractions = function() {
  var opts = {
    fractions: true,
    rollPeriod: 2,
    labels: ['x', 'A']
  };
  var data = [ [1, [1, 10]],
               [2, [2, 10]],
               [3, [3, 10]],
               [4, [4, 10]]
              ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  var rolled = this.getRolledData(g, data, 1, 2);
  assertEquals([1, 10], rolled[0]);
  assertEquals([2, 15], rolled[1]);
  assertEquals([3, 25], rolled[2]);
  assertEquals([4, 35], rolled[3]);
};

rollingAverageTestCase.prototype.testRollFractionsBars = function() {
  var opts = {
    fractions: true,
    errorBars: true,
    wilsonInterval: false,
    rollPeriod: 2,
    labels: ['x', 'A']
  };
  var data = [ [1, [1, 10]],
               [2, [2, 10]],
               [3, [3, 10]],
               [4, [4, 10]]
              ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  var rolled = this.getRolledData(g, data, 1, 2);

  // precalculated rounded values expected
  var values = [10, 15, 25, 35];
  var lows = [-9, -1, 6, 14];
  var highs = [29, 31, 44, 56];

  for (var i=0;i<data.length;i++) {
    assertEquals("unexpected rolled average", values[i], Math.round(rolled[i][1]));
    assertEquals("unexpected rolled min", lows[i], Math.round(rolled[i][2][0]));
    assertEquals("unexpected rolled max", highs[i], Math.round(rolled[i][2][1]));
  }
};

rollingAverageTestCase.prototype.testRollFractionsBarsWilson = function() {
  var opts = {
    fractions: true,
    errorBars: true,
    wilsonInterval: true,
    rollPeriod: 2,
    labels: ['x', 'A']
  };
  var data = [ [1, [1, 10]],
               [2, [2, 10]],
               [3, [3, 10]],
               [4, [4, 10]]
              ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  var rolled = this.getRolledData(g, data, 1, 2);

  //precalculated rounded values expected
  var values = [10, 15, 25, 35];
  var lows = [2, 5, 11, 18];
  var highs = [41, 37, 47, 57];

  for (var i=0;i<data.length;i++) {
    assertEquals("unexpected rolled average", values[i], Math.round(rolled[i][1]));
    assertEquals("unexpected rolled min", lows[i], Math.round(rolled[i][2][0]));
    assertEquals("unexpected rolled max", highs[i], Math.round(rolled[i][2][1]));
  }
};

rollingAverageTestCase.prototype.getRolledData = function(g, data, seriesIdx, rollPeriod){
  var options = g.attributes_;
  return g.dataHandler_.rollingAverage(g.dataHandler_.extractSeries(data, seriesIdx, options), rollPeriod, options);
};
