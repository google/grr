/**
 * @fileoverview Tests that we don'show specify hours, minutes or seconds
 * in your dates if you don't specify them. This can get mixed up becaues of
 * time zones.
 *
 * @author danvk@google.com (Dan Vanderkam)
 */
var noHoursTestCase = TestCase("no-hours");

noHoursTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

noHoursTestCase.prototype.tearDown = function() {
};

noHoursTestCase.prototype.testNoHours = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "Date,Y\n" +
      "2012/03/13,-1\n" +
      "2012/03/14,0\n" +
      "2012/03/15,1\n" +
      "2012/03/16,0\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  g.setSelection(0);
  assertEquals("2012/03/13: Y: -1", Util.getLegend());

  g.setSelection(1);
  assertEquals("2012/03/14: Y: 0", Util.getLegend());

  g.setSelection(2);
  assertEquals("2012/03/15: Y: 1", Util.getLegend());

  g.setSelection(3);
  assertEquals("2012/03/16: Y: 0", Util.getLegend());
};

noHoursTestCase.prototype.testNoHoursDashed = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "Date,Y\n" +
      "2012-03-13,-1\n" +
      "2012-03-14,0\n" +
      "2012-03-15,1\n" +
      "2012-03-16,0\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  g.setSelection(0);
  assertEquals("2012/03/13: Y: -1", Util.getLegend());

  g.setSelection(1);
  assertEquals("2012/03/14: Y: 0", Util.getLegend());

  g.setSelection(2);
  assertEquals("2012/03/15: Y: 1", Util.getLegend());

  g.setSelection(3);
  assertEquals("2012/03/16: Y: 0", Util.getLegend());
};

