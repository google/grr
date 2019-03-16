/** 
 * @fileoverview Test cases for DygraphOptions.
 */
var DygraphOptionsTestCase = TestCase("dygraph-options-tests");

DygraphOptionsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

DygraphOptionsTestCase.prototype.tearDown = function() {
};

/*
 * Pathalogical test to ensure getSeriesNames works
 */
DygraphOptionsTestCase.prototype.testGetSeriesNames = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,Y,Y2,Y3\n" +
      "0,-1,0,0";

  // Kind of annoying that you need a DOM to test the object.
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  // We don't need to get at g's attributes_ object just
  // to test DygraphOptions.
  var o = new DygraphOptions(g);
  assertEquals(["Y", "Y2", "Y3"], o.seriesNames()); 
};

/*
 * Ensures that even if logscale is set globally, it doesn't impact the
 * x axis.
 */
DygraphOptionsTestCase.prototype.testGetLogscaleForX = function() {
  var opts = {
    width: 480,
    height: 320
  };
  var data = "X,Y,Y2,Y3\n" +
      "1,-1,2,3";

  // Kind of annoying that you need a DOM to test the object.
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);

  assertFalse(!!g.getOptionForAxis('logscale', 'x'));
  assertFalse(!!g.getOptionForAxis('logscale', 'y'));

  g.updateOptions({ logscale : true });
  assertFalse(!!g.getOptionForAxis('logscale', 'x'));
  assertTrue(!!g.getOptionForAxis('logscale', 'y'));
};

// Helper to gather all warnings emitted by Dygraph constructor.
// Removes everything after the first open parenthesis in each warning.
// Returns them in a (possibly empty) list.
var getWarnings = function(div, data, opts) {
  var warnings = [];
  var oldWarn = console.warn;
  console.warn = function(message) {
    warnings.push(message.replace(/ \(.*/, ''));
  };
  try {
    new Dygraph(graph, data, opts);
  } catch (e) {
  }
  console.warn = oldWarn;
  return warnings;
};

DygraphOptionsTestCase.prototype.testLogWarningForNonexistentOption = function() {
  if (typeof(Dygraph.OPTIONS_REFERENCE) === 'undefined') {
    return;  // this test won't pass in non-debug mode.
  }

  var graph = document.getElementById("graph");
  var data = "X,Y,Y2,Y3\n" +
      "1,-1,2,3";

  var expectWarning = function(opts, badOptionName) {
    DygraphOptions.resetWarnings_();
    var warnings = getWarnings(graph, data, opts);
    assertEquals(['Unknown option ' + badOptionName], warnings);
  };
  var expectNoWarning = function(opts) {
    DygraphOptions.resetWarnings_();
    var warnings = getWarnings(graph, data, opts);
    assertEquals([], warnings);
  };

  expectNoWarning({});
  expectWarning({nonExistentOption: true}, 'nonExistentOption');
  expectWarning({series: {Y: {nonExistentOption: true}}}, 'nonExistentOption');
  // expectWarning({Y: {nonExistentOption: true}});
  expectWarning({axes: {y: {anotherNonExistentOption: true}}}, 'anotherNonExistentOption');
  expectWarning({highlightSeriesOpts: {anotherNonExistentOption: true}}, 'anotherNonExistentOption');
  expectNoWarning({highlightSeriesOpts: {strokeWidth: 20}});
  expectNoWarning({strokeWidth: 20});
};

DygraphOptionsTestCase.prototype.testOnlyLogsEachWarningOnce = function() {
  if (typeof(Dygraph.OPTIONS_REFERENCE) === 'undefined') {
    return;  // this test won't pass in non-debug mode.
  }

  var graph = document.getElementById("graph");
  var data = "X,Y,Y2,Y3\n" +
      "1,-1,2,3";

  var warnings1 = getWarnings(graph, data, {nonExistent: true});
  var warnings2 = getWarnings(graph, data, {nonExistent: true});
  assertEquals(['Unknown option nonExistent'], warnings1);
  assertEquals([], warnings2);
};
