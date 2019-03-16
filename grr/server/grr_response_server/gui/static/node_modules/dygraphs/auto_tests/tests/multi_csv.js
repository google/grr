/** 
 * @fileoverview Test cases for how axis labels are chosen and formatted.
 *
 * @author dan@dygraphs.com (Dan Vanderkam)
 */
var MultiCsvTestCase = TestCase("multi-csv");

MultiCsvTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

MultiCsvTestCase.prototype.tearDown = function() {
};

function getXLabels() {
  var x_labels = document.getElementsByClassName("dygraph-axis-label-x");
  var ary = [];
  for (var i = 0; i < x_labels.length; i++) {
    ary.push(x_labels[i].innerHTML);
  }
  return ary;
}

MultiCsvTestCase.prototype.testOneCSV = function() {
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

  assertEquals(['0', '1', '2'], getXLabels());
};

MultiCsvTestCase.prototype.testTwoCSV = function() {
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

  assertEquals(['0', '1', '2'], getXLabels());

  g.updateOptions({file: data});

  assertEquals(['0', '1', '2'], getXLabels());
};
