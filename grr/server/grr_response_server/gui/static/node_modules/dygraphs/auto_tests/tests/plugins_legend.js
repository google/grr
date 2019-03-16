/**
 * @fileoverview FILL THIS IN
 *
 * @author akiya.mizukoshi@gmail.com (Akiyah)
 */
var pluginsLegendTestCase = TestCase("plugins-legend");

pluginsLegendTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

pluginsLegendTestCase.prototype.tearDown = function() {
};

pluginsLegendTestCase.prototype.testLegendEscape = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,<script>alert('XSS')</script>\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  var legendPlugin = new Dygraph.Plugins.Legend();
  legendPlugin.activate(g);
  var e = {
    selectedX: 'selectedX',
    selectedPoints: [{
      canvasy: 100,
      name: "<script>alert('XSS')</script>",
      yval: 10,
    }],
    dygraph: g
  }
  legendPlugin.select(e);

  var legendSpan = $(legendPlugin.legend_div_).find("span b span");
  assertEquals("&lt;script&gt;alert('XSS')&lt;/script&gt;", legendSpan.html());
};

