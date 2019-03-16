/**
 * @fileoverview Test cases for the option "stepPlot" especially for the scenario where the option is not set for the whole graph but for single series.
 *
 * TODO(danvk): delete this test once dpxdt screenshot tests are part of the
 *     main dygraphs repo. The tests have extremely specific expectations about
 *     how drawing is performed. It's more realistic to test the resulting
 *     pixels.
 *
 * @author julian.eichstaedt@ch.sauter-bc.com (Fr. Sauter AG)
 */
var StepTestCase = TestCase("step-plot-per-series");

StepTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

StepTestCase.origFunc = Dygraph.getContext;

StepTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
  Dygraph.getContext = function(canvas) {
    return new Proxy(StepTestCase.origFunc(canvas));
  };
};

StepTestCase.prototype.tearDown = function() {
  Dygraph.getContext = StepTestCase.origFunc;
};

StepTestCase.prototype.testMixedModeStepAndLineFilled = function() {
  var opts = {
    width: 480,
    height: 320,
    drawXGrid: false,
    drawYGrid: false,
    drawXAxis: false,
    drawYAxis: false,
    errorBars: false,
    labels: ["X", "Idle", "Used"],
    series: {
      Idle: {stepPlot: false},
      Used: {stepPlot: true}
    },
    fillGraph: true,
    stackedGraph: false,
    includeZero: true
  };

  var data = [
               [1, 70,30],
               [2, 12,88],
               [3, 88,12],
               [4, 63,37],
               [5, 35,65]
             ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  htx = g.hidden_ctx_;

  var attrs = {};  


  for (var i = 0; i < data.length - 1; i++) {

    var x1 = data[i][0];
    var x2 = data[i + 1][0];

    var y1 = data[i][1];
    var y2 = data[i + 1][1];

    // First series (line)
    var xy1 = g.toDomCoords(x1, y1);
    var xy2 = g.toDomCoords(x2, y2);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    y1 = data[i][2];
    y2 = data[i + 1][2];

    // Seconds series (step)
    // Horizontal line
    xy1 = g.toDomCoords(x1, y1);
    xy2 = g.toDomCoords(x2, y1);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // Vertical line
    xy1 = g.toDomCoords(x2, y1);
    xy2 = g.toDomCoords(x2, y2);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  }
};

StepTestCase.prototype.testMixedModeStepAndLineStackedAndFilled = function() {
  var opts = {
    width: 480,
    height: 320,
    drawXGrid: false,
    drawYGrid: false,
    drawXAxis: false,
    drawYAxis: false,
    errorBars: false,
    labels: ["X", "Idle", "Used", "NotUsed", "Active"],
    series: {
      Idle: {stepPlot: false},
      Used: {stepPlot: true},
      NotUsed: {stepPlot: false},
      Active: {stepPlot: true}
    },
    fillGraph: true,
    stackedGraph: true,
    includeZero: true
  };

  var data = [
               [1, 60,30,5,5],
               [2, 12,73,5,10],
               [3, 38,12,30,20],
               [4, 50,17,23,10],
               [5, 35,25,35,5]
             ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  htx = g.hidden_ctx_;

  var attrs = {};  


  for (var i = 0; i < data.length - 1; i++) {
    
    var x1 = data[i][0];
    var x2 = data[i + 1][0];
    var y1base = 0;
    var y2base = 0;
    var y1 = data[i][4];
    var y2 = data[i + 1][4];

    // Fourth series (step)
    // Test lines
    // Horizontal line
    var xy1 = g.toDomCoords(x1, y1);
    var xy2 = g.toDomCoords(x2, y1);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // Vertical line
    xy1 = g.toDomCoords(x2, y1);
    xy2 = g.toDomCoords(x2, y2);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // Test edges of areas (also drawn by dygraphs as lines)
    xy1 = g.toDomCoords(x1, y1);
    xy2 = g.toDomCoords(x2, y1);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x2, y2base);
    // CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x1, y1base);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // The last edge can not be tested via assertLineDrawn since it wasn't drawn as a line but via clossePath.
    // But a rectangle is completely tested with three of its four edges.
    
    y1base = y1;
    y2base = y1;
    y1 += data[i][3];
    y2 += data[i + 1][3];
    
    // Third series (line)
    // Test lines
    xy1 = g.toDomCoords(x1, y1);
    xy2 = g.toDomCoords(x2, y2);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // Test edges of areas (also drawn by dygraphs as lines)
    xy1 = g.toDomCoords(x1, y1);
    xy2 = g.toDomCoords(x2, y2);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x2, y2base);
    // CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x1, y1base);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // The last edge can not be tested via assertLineDrawn since it wasn't drawn as a line but via clossePath.
    // But a rectangle is completely tested with three of its four edges.
    
    y1base = y1;
    y2base = y2;
    y1 += data[i][2];
    y2 += data[i + 1][2];

    // Second series (step)
    // Test lines
    // Horizontal line
    xy1 = g.toDomCoords(x1, y1);
    xy2 = g.toDomCoords(x2, y1);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // Vertical line
    xy1 = g.toDomCoords(x2, y1);
    xy2 = g.toDomCoords(x2, y2);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // Test edges of areas (also drawn by dygraphs as lines)
    xy1 = g.toDomCoords(x1, y1);
    xy2 = g.toDomCoords(x2, y1);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x2, y2base);
    // CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x1, y1base);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // The last edge can not be tested via assertLineDrawn since it wasn't drawn as a line but via clossePath.
    // But a rectangle is completely tested with three of its four edges.
    
    y1base = y1;
    y2base = y1;
    y1 += data[i][1];
    y2 += data[i + 1][1];

    // First series (line)
    // Test lines
    xy1 = g.toDomCoords(x1, y1);
    xy2 = g.toDomCoords(x2, y2);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // Test edges of areas (also drawn by dygraphs as lines)
    xy1 = g.toDomCoords(x1, y1);
    xy2 = g.toDomCoords(x2, y2);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x2, y2base);
    // CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x1, y1base);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // The last edge can not be tested via assertLineDrawn since it wasn't drawn as a line but via clossePath.
    // But a rectangle is completely tested with three of its four edges.
  }
};

StepTestCase.prototype.testMixedModeStepAndLineErrorBars = function() {
  var opts = {
    width: 480,
    height: 320,
    drawXGrid: false,
    drawYGrid: false,
    drawXAxis: false,
    drawYAxis: false,
    errorBars: true,
    sigma: 1,
    labels: ["X", "Data1", "Data2"],
    series: {
      Data1: {stepPlot: true},	
      Data2: {stepPlot: false} 
    }
  };
  var data = [
               [1, [75, 2], [50, 3]],
               [2, [70, 5], [90, 4]],
               [3, [80, 7], [112, 5]],
               [4, [55, 3], [100, 2]],
               [5, [69, 4], [85, 6]]
             ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  htx = g.hidden_ctx_;

  var attrs = {};  

  // Test first series (step)
  for (var i = 0; i < data.length - 1; i++) {
    var x1 = data[i][0];
    var x2 = data[i + 1][0];
    
    var y1_middle = data[i][1][0];
    var y2_middle = data[i + 1][1][0];
    
    var y1_top = y1_middle + data[i][1][1];
    var y2_top = y2_middle + data[i + 1][1][1];
    
    var y1_bottom = y1_middle - data[i][1][1];
    var y2_bottom = y2_middle - data[i + 1][1][1];
    // Bottom line
    var xy1 = g.toDomCoords(x1, y1_bottom);
    var xy2 = g.toDomCoords(x2, y1_bottom);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // Top line
    xy1 = g.toDomCoords(x1, y1_top);
    xy2 = g.toDomCoords(x2, y1_top);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // Middle line
    xy1 = g.toDomCoords(x1, y1_middle);
    xy2 = g.toDomCoords(x2, y1_middle);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    
    // Test edges of error bar areas(also drawn by dygraphs as lines)
    xy1 = g.toDomCoords(x1, y1_top);
    xy2 = g.toDomCoords(x2, y1_top);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x2, y1_bottom);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x1, y1_bottom);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // The last edge can not be tested via assertLineDrawn since it wasn't drawn as a line but via clossePath.
    // But a rectangle is completely tested with three of its four edges.
  }

  // Test second series (line)  
  for (var i = 0; i < data.length - 1; i++) {
    // bottom line
    var xy1 = g.toDomCoords(data[i][0], (data[i][2][0] - data[i][2][1]));
    var xy2 = g.toDomCoords(data[i + 1][0], (data[i + 1][2][0] - data[i + 1][2][1]));
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // top line
    xy1 = g.toDomCoords(data[i][0], data[i][2][0] + data[i][2][1]);
    xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][2][0] + data[i + 1][2][1]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // middle line
    xy1 = g.toDomCoords(data[i][0], data[i][2][0]);
    xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][2][0]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  }

};

StepTestCase.prototype.testMixedModeStepAndLineCustomBars = function() {
  var opts = {
    width: 480,
    height: 320,
    drawXGrid: false,
    drawYGrid: false,
    drawXAxis: false,
    drawYAxis: false,
    customBars: true,
	labels: ["X", "Data1", "Data2"],
    series: {
      Data1: {stepPlot: true},	
      Data2: {stepPlot: false} 
    }
  };
  var data = [
               [1, [73, 75, 78], [50, 55, 70]],
               [2, [65, 70, 75], [83, 91, 99]],
               [3, [75, 85, 90], [98, 107, 117]],
               [4, [55, 58, 61], [93, 102, 105]],
               [5, [69, 73, 85], [80, 85, 87]]
             ];

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  htx = g.hidden_ctx_;

  var attrs = {};  

  // Test first series (step)
  for (var i = 0; i < data.length - 1; i++) {

    var x1 = data[i][0];
    var x2 = data[i + 1][0];
    
    var y1_middle = data[i][1][1];
    var y2_middle = data[i + 1][1][1];
    
    var y1_top = data[i][1][2];
    var y2_top = data[i + 1][1][2];
    
    var y1_bottom = data[i][1][0];
    var y2_bottom = data[i + 1][1][0];
    
    // Bottom line
    var xy1 = g.toDomCoords(x1, y1_bottom);
    var xy2 = g.toDomCoords(x2, y1_bottom);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    
    // Top line
    xy1 = g.toDomCoords(x1, y1_top);
    xy2 = g.toDomCoords(x2, y1_top);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    
    // Middle line
    xy1 = g.toDomCoords(x1, y1_middle);
    xy2 = g.toDomCoords(x2, y1_middle);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    
    // Test edges of custom bar areas(also drawn by dygraphs as lines)
    xy1 = g.toDomCoords(x1, y1_top);
    xy2 = g.toDomCoords(x2, y1_top);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x2, y1_bottom);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    xy1 = xy2;
    xy2 = g.toDomCoords(x1, y1_bottom);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
    // The last edge can not be tested via assertLineDrawn since it wasn't drawn as a line but via clossePath.
    // But a rectangle is completely tested with three of its four edges.
  }
  
  // Test second series (line)
  for (var i = 0; i < data.length - 1; i++) {
    // Bottom line
    var xy1 = g.toDomCoords(data[i][0], data[i][2][0]);
    var xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][2][0]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // Top line
    xy1 = g.toDomCoords(data[i][0], data[i][2][2]);
    xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][2][2]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);

    // Middle line
    xy1 = g.toDomCoords(data[i][0], data[i][2][1]);
    xy2 = g.toDomCoords(data[i + 1][0], data[i + 1][2][1]);
    CanvasAssertions.assertLineDrawn(htx, xy1, xy2, attrs);
  }
};
