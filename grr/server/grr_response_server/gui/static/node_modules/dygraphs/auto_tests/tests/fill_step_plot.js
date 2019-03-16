/**
 * @fileoverview Test if you give null values to dygraph with stepPlot
 * and fillGraph options enabled
 *
 * @author benoitboivin.pro@gmail.com (Benoit Boivin)
 */
var fillStepPlotTestCase = TestCase("fill-step-plot");

fillStepPlotTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

fillStepPlotTestCase.origFunc = Dygraph.getContext;

fillStepPlotTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
  Dygraph.getContext = function(canvas) {
    return new Proxy(fillStepPlotTestCase.origFunc(canvas));
  };
};

fillStepPlotTestCase.prototype.tearDown = function() {
  Dygraph.getContext = fillStepPlotTestCase.origFunc;
};


fillStepPlotTestCase.prototype.testFillStepPlotNullValues = function() {
  var opts = {
    labels: ["x","y"],
    width: 480,
    height: 320,
    fillGraph: true,
    stepPlot: true
  };
  var data = [
    [1,3],
    [2,0],
    [3,8],
    [4,null],
    [5,9],
    [6,8],
    [7,6],
    [8,3]
  ];
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  htx = g.hidden_ctx_;
  var x1 = data[3][0];
  var y1 = data[2][1];
  var x2 = data[3][0];
  var y2 = 0;
  var xy1 = g.toDomCoords(x1, y1);
  var xy2 = g.toDomCoords(x2, y2);
  
  // Check if a line is drawn between the previous y and the bottom of the chart
  CanvasAssertions.assertLineDrawn(htx, xy1, xy2, {});
};