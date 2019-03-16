/**
 * @fileoverview Tests the way that dygraphs parses data.
 *
 * @author danvk@google.com (Dan Vanderkam)
 */
var parserTestCase = TestCase("parser");

parserTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

parserTestCase.prototype.tearDown = function() {
};

parserTestCase.prototype.testDetectLineDelimiter = function() {
  var data = "X,Y\r" +
      "0,-1\r" +
      "1,0\r" +
      "2,1\r" +
      "3,0\r"
  ;
  assertEquals("\r", Dygraph.detectLineDelimiter(data));

  data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;
  assertEquals("\n", Dygraph.detectLineDelimiter(data));

  data = "X,Y\n\r" +
      "0,-1\n\r" +
      "1,0\n\r" +
      "2,1\n\r" +
      "3,0\n\r"
  ;
  assertEquals("\n\r", Dygraph.detectLineDelimiter(data));
};

parserTestCase.prototype.testParseDosNewlines = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,Y\r" +
      "0,-1\r" +
      "1,0\r" +
      "2,1\r" +
      "3,0\r"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  assertEquals(0, g.getValue(0, 0));
  assertEquals(-1, g.getValue(0, 1));
  assertEquals(1, g.getValue(1, 0));
  assertEquals(0, g.getValue(1, 1));
  assertEquals(['X', 'Y'], g.getLabels());
};

