/**
 * @fileoverview Tests for per-axis options.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
var perAxisTestCase = TestCase("per-axis");

perAxisTestCase._origGetContext = Dygraph.getContext;

perAxisTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
  Dygraph.getContext = function(canvas) {
    return new Proxy(perAxisTestCase._origGetContext(canvas));
  }

  this.xAxisLineColor = "#00ffff";
  this.yAxisLineColor = "#ffff00";

  var opts = {
    axes : {
      x : {
        drawAxis : false,
        drawGrid : false,
        gridLineColor : this.xAxisLineColor
      },
      y : {
        drawAxis : false,
        drawGrid : false,
        gridLineColor : this.yAxisLineColor
      }
    },
    colors: [ '#ff0000', '#0000ff' ]
  };

  var data = "X,Y,Z\n" +
      "1,1,0\n" +
      "8,0,1\n"
  ;
  this.graph = document.getElementById('graph');
  this.g = new Dygraph(this.graph, data, opts);
};

perAxisTestCase.prototype.tearDown = function() {
  Dygraph.getContext = perAxisTestCase._origGetContext;
};

perAxisTestCase.prototype.testDrawXAxis = function() {
  this.g.updateOptions({ drawXAxis : true });
  assertTrue(this.graph.getElementsByClassName('dygraph-axis-label-x').length > 0);
  assertTrue(this.graph.getElementsByClassName('dygraph-axis-label-y').length == 0);
}

perAxisTestCase.prototype.testDrawYAxis = function() {
  this.g.updateOptions({ drawYAxis : true });
  assertTrue(this.graph.getElementsByClassName('dygraph-axis-label-x').length ==0);
  assertTrue(this.graph.getElementsByClassName('dygraph-axis-label-y').length > 0);
}

perAxisTestCase.prototype.testDrawAxisX = function() {
  this.g.updateOptions({ axes : { x : { drawAxis : true }}});
  assertTrue(this.graph.getElementsByClassName('dygraph-axis-label-x').length > 0);
  assertTrue(this.graph.getElementsByClassName('dygraph-axis-label-y').length == 0);
}

perAxisTestCase.prototype.testDrawAxisY = function() {
  this.g.updateOptions({ axes : { y : { drawAxis : true }}});
  assertTrue(this.graph.getElementsByClassName('dygraph-axis-label-x').length ==0);
  assertTrue(this.graph.getElementsByClassName('dygraph-axis-label-y').length > 0);
}
perAxisTestCase.prototype.testDrawXGrid = function() {
  this.g.updateOptions({ drawXGrid : true });
  var htx = this.g.hidden_ctx_;
  assertTrue(CanvasAssertions.numLinesDrawn(htx, this.xAxisLineColor) > 0);
  assertTrue(CanvasAssertions.numLinesDrawn(htx, this.yAxisLineColor) == 0);
}

perAxisTestCase.prototype.testDrawYGrid = function() {
  this.g.updateOptions({ drawYGrid : true });
  var htx = this.g.hidden_ctx_;
  assertTrue(CanvasAssertions.numLinesDrawn(htx, this.xAxisLineColor) == 0);
  assertTrue(CanvasAssertions.numLinesDrawn(htx, this.yAxisLineColor) > 0);
}

perAxisTestCase.prototype.testDrawGridX = function() {
  this.g.updateOptions({ axes : { x : { drawGrid : true }}});
  var htx = this.g.hidden_ctx_;
  assertTrue(CanvasAssertions.numLinesDrawn(htx, this.xAxisLineColor) > 0);
  assertTrue(CanvasAssertions.numLinesDrawn(htx, this.yAxisLineColor) == 0);
}

perAxisTestCase.prototype.testDrawGridY = function() {
  this.g.updateOptions({ axes : { y : { drawGrid : true }}});
  var htx = this.g.hidden_ctx_;
  assertTrue(CanvasAssertions.numLinesDrawn(htx, this.xAxisLineColor) == 0);
  assertTrue(CanvasAssertions.numLinesDrawn(htx, this.yAxisLineColor) > 0);
}
