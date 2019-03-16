/**
 * @fileoverview Tests for the plugins option.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
var pluginsTestCase = TestCase("plugins");

pluginsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";

  this.data = "X,Y1,Y2\n" +
      "0,1,2\n" +
      "1,2,1\n" +
      "2,1,2\n" +
      "3,2,1\n"
  ;
};

pluginsTestCase.prototype.tearDown = function() {
};

pluginsTestCase.prototype.testWillDrawChart = function() {
  var draw = 0;

  var plugin = (function() {
    var p = function() {
    };  

    p.prototype.activate = function(g) {
      return {
        willDrawChart: this.willDrawChart
      };
    };

    p.prototype.willDrawChart = function(e) {
      draw++;
    };

    return p;
  })();

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, this.data, {plugins: [plugin]});

  assertEquals(1, draw);
};

pluginsTestCase.prototype.testPassingInstance = function() {
  // You can also pass an instance of a plugin instead of a Plugin class.
  var draw = 0;
  var p = {
    activate: function(g) {
      return {
        willDrawChart: this.willDrawChart
      }
    },
    willDrawChart: function(g) {
      draw++;
    }
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, this.data, {plugins: [p]});

  assertEquals(1, draw);
};

pluginsTestCase.prototype.testPreventDefault = function() {
  var data1 = "X,Y\n" +
      "20,-1\n" +
      "21,0\n" +
      "22,1\n" +
      "23,0\n";

  var events = [];

  var p = {
    pointClickPreventDefault: false,
    clickPreventDefault: false,
    activate: function(g) {
      return {
        pointClick: this.pointClick,
        click: this.click
      }
    },
    pointClick: function(e) {
      events.push(['plugin.pointClick', e.point.xval, e.point.yval]);
      if (this.pointClickPreventDefault) {
        e.preventDefault();
      }
    },
    click: function(e) {
      events.push(['plugin.click', e.xval]);
      if (this.clickPreventDefault) {
        e.preventDefault();
      }
    }
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data1, {
    plugins: [p],
    clickCallback: function(e, x) {
      events.push(['clickCallback', x]);
    },
    pointClickCallback: function(e, pt) {
      events.push(['pointClickCallback', pt.xval, pt.yval]);
    }
  });

  // Click the point at x=20
  function clickOnPoint() {
    var x = 58, y = 275;
    DygraphOps.dispatchMouseDown_Point(g, x, y);
    DygraphOps.dispatchMouseMove_Point(g, x, y);
    DygraphOps.dispatchMouseUp_Point(g, x, y);
  }

  p.pointClickPreventDefault = false;
  p.clickPreventDefault = false;
  clickOnPoint();
  assertEquals([
    ['plugin.pointClick', 20, -1],
    ['pointClickCallback', 20, -1],
    ['plugin.click', 20],
    ['clickCallback', 20]
  ], events);

  events = [];
  p.pointClickPreventDefault = true;
  p.clickPreventDefault = false;
  clickOnPoint();
  assertEquals([
    ['plugin.pointClick', 20, -1]
  ], events);

  events = [];
  p.pointClickPreventDefault = false;
  p.clickPreventDefault = true;
  clickOnPoint();
  assertEquals([
    ['plugin.pointClick', 20, -1],
    ['pointClickCallback', 20, -1],
    ['plugin.click', 20]
  ], events);
};

pluginsTestCase.prototype.testEventSequence = function() {
  var events = [];

  var eventLogger = function(name) {
    return function(e) {
      events.push(name);
    };
  };

  var p = {
    activate: function(g) {
      return {
        clearChart: eventLogger('clearChart'),
        predraw: eventLogger('predraw'),
        willDrawChart: eventLogger('willDrawChart'),
        didDrawChart: eventLogger('didDrawChart'),
        dataWillUpdate: eventLogger('dataWillUpdate'),
        dataDidUpdate: eventLogger('dataDidUpdate')
      }
    }
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, this.data, {plugins: [p]});

  // Initial draw sequence
  assertEquals([
   "dataDidUpdate",  // should dataWillUpdate be called here, too?
   "predraw",
   "clearChart",
   "willDrawChart",
   "didDrawChart"
  ], events);

  // An options change triggers a redraw, but doesn't change the data.
  events = [];
  g.updateOptions({series: {Y1: {color: 'blue'}}});
  assertEquals([
   "predraw",
   "clearChart",
   "willDrawChart",
   "didDrawChart"
  ], events);

  // A pan shouldn't cause a new "predraw"
  events = [];
  DygraphOps.dispatchMouseDown_Point(g, 100, 100, {shiftKey: true});
  DygraphOps.dispatchMouseMove_Point(g, 200, 100, {shiftKey: true});
  DygraphOps.dispatchMouseUp_Point(g, 200, 100, {shiftKey: true});
  assertEquals([
   "clearChart",
   "willDrawChart",
   "didDrawChart"
  ], events);

  // New data triggers the full sequence.
  events = [];
  g.updateOptions({file: this.data + '\n4,1,2'});
  assertEquals([
   "dataWillUpdate",
   "dataDidUpdate",
   "predraw",
   "clearChart",
   "willDrawChart",
   "didDrawChart"
  ], events);
};

pluginsTestCase.prototype.testDestroyCalledInOrder = function() {
  var destructions = [];
  var makePlugin = function(name) {
    return {
      activate: function(g) { return {} },
      destroy: function() {
        destructions.push(name);
      }
    };
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, this.data, {
    plugins: [makePlugin('p'), makePlugin('q')]
  });

  assertEquals([], destructions);
  g.destroy();
  assertEquals(['q', 'p'], destructions);
};
