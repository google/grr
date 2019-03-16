/** 
 * @fileoverview Test cases for the interaction model.
 *
 * @author konigsberg@google.com (Robert Konigsbrg)
 */
var InteractionModelTestCase = TestCase("interaction-model");

InteractionModelTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

InteractionModelTestCase.prototype.tearDown = function() {
};

var data1 = "X,Y\n" +
    "20,-1\n" +
    "21,0\n" +
    "22,1\n" +
    "23,0\n";

var data2 =
    [[1, 10],
    [2, 20],
    [3, 30],
    [4, 40],
    [5, 120],
    [6, 50],
    [7, 70],
    [8, 90],
    [9, 50]];

function getXLabels() {
  var x_labels = document.getElementsByClassName("dygraph-axis-label-x");
  var ary = [];
  for (var i = 0; i < x_labels.length; i++) {
    ary.push(x_labels[i].innerHTML);
  }
  return ary;
}

InteractionModelTestCase.prototype.pan = function(g, xRange, yRange) {
  var originalXRange = g.xAxisRange();
  var originalYRange = g.yAxisRange(0);

  DygraphOps.dispatchMouseDown(g, xRange[0], yRange[0]);
  DygraphOps.dispatchMouseMove(g, xRange[1], yRange[0]); // this is really necessary.
  DygraphOps.dispatchMouseUp(g, xRange[1], yRange[0]);

  assertEqualsDelta(xRange, g.xAxisRange(), 0.2);
  // assertEqualsDelta(originalYRange, g.yAxisRange(0), 0.2); // Not true, it's something in the middle.

  var midX = (xRange[1] - xRange[0]) / 2;
  DygraphOps.dispatchMouseDown(g, midX, yRange[0]);
  DygraphOps.dispatchMouseMove(g, midX, yRange[1]); // this is really necessary.
  DygraphOps.dispatchMouseUp(g, midX, yRange[1]);

  assertEqualsDelta(xRange, g.xAxisRange(), 0.2);
  assertEqualsDelta(yRange, g.yAxisRange(0), 0.2);
}

/**
 * This tests that when changing the interaction model so pan is used instead
 * of zoom as the default behavior, a standard click method is still called.
 */
InteractionModelTestCase.prototype.testClickCallbackIsCalled = function() {
  var clicked;

  var clickCallback = function(event, x) {
    clicked = x;
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data1,
      {
        width: 100,
        height : 100,
        clickCallback : clickCallback
      });

  DygraphOps.dispatchMouseDown_Point(g, 10, 10);
  DygraphOps.dispatchMouseMove_Point(g, 10, 10);
  DygraphOps.dispatchMouseUp_Point(g, 10, 10);

  assertEquals(20, clicked);
};

/**
 * This tests that when changing the interaction model so pan is used instead
 * of zoom as the default behavior, a standard click method is still called.
 */
InteractionModelTestCase.prototype.testClickCallbackIsCalledOnCustomPan = function() {
  var clicked;

  var clickCallback = function(event, x) {
    clicked = x;
  };

  function customDown(event, g, context) {
    context.initializeMouseDown(event, g, context);
    Dygraph.startPan(event, g, context);
  }

  function customMove(event, g, context) {
    Dygraph.movePan(event, g, context);
  }

  function customUp(event, g, context) {
    Dygraph.endPan(event, g, context);
  }

  var opts = {
    width: 100,
    height : 100,
    clickCallback : clickCallback,
    interactionModel : {
      'mousedown' : customDown,
      'mousemove' : customMove,
      'mouseup' : customUp,
    }
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data1, opts);

  DygraphOps.dispatchMouseDown_Point(g, 10, 10);
  DygraphOps.dispatchMouseMove_Point(g, 10, 10);
  DygraphOps.dispatchMouseUp_Point(g, 10, 10);

  assertEquals(20, clicked);
};

InteractionModelTestCase.clickAt = function(g, x, y) {
  DygraphOps.dispatchMouseDown(g, x, y);
  DygraphOps.dispatchMouseMove(g, x, y);
  DygraphOps.dispatchMouseUp(g, x, y);
}

/**
 * This tests that clickCallback is still called with the nonInteractiveModel.
 */
InteractionModelTestCase.prototype.testClickCallbackIsCalledWithNonInteractiveModel = function() {
  var clicked;

  // TODO(danvk): also test pointClickCallback here.
  var clickCallback = function(event, x) {
    clicked = x;
  };

  var opts = {
    width: 100,
    height : 100,
    clickCallback : clickCallback,
    interactionModel : Dygraph.Interaction.nonInteractiveModel_
  };

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data1, opts);

  DygraphOps.dispatchMouseDown_Point(g, 10, 10);
  DygraphOps.dispatchMouseMove_Point(g, 10, 10);
  DygraphOps.dispatchMouseUp_Point(g, 10, 10);

  assertEquals(20, clicked);
};

/**
 * A sanity test to ensure pointClickCallback is called.
 */
InteractionModelTestCase.prototype.testPointClickCallback = function() {
  var clicked;
  var g = new Dygraph(document.getElementById("graph"), data2, {
    pointClickCallback : function(event, point) {
      clicked = point;
    }
  });

  InteractionModelTestCase.clickAt(g, 4, 40);

  assertEquals(4, clicked.xval);
  assertEquals(40, clicked.yval);
};

/**
 * A sanity test to ensure pointClickCallback is not called when out of range.
 */
InteractionModelTestCase.prototype.testNoPointClickCallbackWhenOffPoint = function() {
  var clicked;
  var g = new Dygraph(document.getElementById("graph"), data2, {
    pointClickCallback : function(event, point) {
      clicked = point;
    }
  });

  InteractionModelTestCase.clickAt(g, 5, 40);

  assertUndefined(clicked);
};

/**
 * Ensures pointClickCallback circle size is taken into account.
 */
InteractionModelTestCase.prototype.testPointClickCallback_circleSize = function() {
  // TODO(konigsberg): Implement.
};

/**
 * Ensures that pointClickCallback is called prior to clickCallback
 */
InteractionModelTestCase.prototype.testPointClickCallbackCalledPriorToClickCallback = function() {
  var counter = 0;
  var pointClicked;
  var clicked;
  var g = new Dygraph(document.getElementById("graph"), data2, {
    pointClickCallback : function(event, point) {
      counter++;
      pointClicked = counter;
    },
    clickCallback : function(event, point) {
      counter++;
      clicked = counter;
    }
  });

  InteractionModelTestCase.clickAt(g, 4, 40);
  assertEquals(1, pointClicked);
  assertEquals(2, clicked);
};

/**
 * Ensures that when there's no pointClickCallback, clicking on a point still calls
 * clickCallback
 */
InteractionModelTestCase.prototype.testClickCallback_clickOnPoint = function() {
  var clicked;
  var g = new Dygraph(document.getElementById("graph"), data2, {
    clickCallback : function(event, point) {
      clicked = 1;
    }
  });

  InteractionModelTestCase.clickAt(g, 4, 40);
  assertEquals(1, clicked);
};

InteractionModelTestCase.prototype.testIsZoomed_none = function() {
  var g = new Dygraph(document.getElementById("graph"), data2, {});

  assertFalse(g.isZoomed());
  assertFalse(g.isZoomed("x"));
  assertFalse(g.isZoomed("y"));
};

InteractionModelTestCase.prototype.testIsZoomed_x = function() {
  var g = new Dygraph(document.getElementById("graph"), data2, {});

  DygraphOps.dispatchMouseDown_Point(g, 100, 100);
  DygraphOps.dispatchMouseMove_Point(g, 130, 100);
  DygraphOps.dispatchMouseUp_Point(g, 130, 100);

  assertTrue(g.isZoomed());
  assertTrue(g.isZoomed("x"));
  assertFalse(g.isZoomed("y"));
};

InteractionModelTestCase.prototype.testIsZoomed_y = function() {
  var g = new Dygraph(document.getElementById("graph"), data2, {});

  DygraphOps.dispatchMouseDown_Point(g, 10, 10);
  DygraphOps.dispatchMouseMove_Point(g, 10, 30);
  DygraphOps.dispatchMouseUp_Point(g, 10, 30);

  assertTrue(g.isZoomed());
  assertFalse(g.isZoomed("x"));
  assertTrue(g.isZoomed("y"));
};

InteractionModelTestCase.prototype.testIsZoomed_both = function() {
  var g = new Dygraph(document.getElementById("graph"), data2, {});

  // Zoom x axis
  DygraphOps.dispatchMouseDown_Point(g, 100, 100);
  DygraphOps.dispatchMouseMove_Point(g, 130, 100);
  DygraphOps.dispatchMouseUp_Point(g, 130, 100);

  // Now zoom y axis
  DygraphOps.dispatchMouseDown_Point(g, 100, 100);
  DygraphOps.dispatchMouseMove_Point(g, 100, 130);
  DygraphOps.dispatchMouseUp_Point(g, 100, 130);


  assertTrue(g.isZoomed());
  assertTrue(g.isZoomed("x"));
  assertTrue(g.isZoomed("y"));
};

InteractionModelTestCase.prototype.testIsZoomed_updateOptions_none = function() {
  var g = new Dygraph(document.getElementById("graph"), data2, {});

  g.updateOptions({});

  assertFalse(g.isZoomed());
  assertFalse(g.isZoomed("x"));
  assertFalse(g.isZoomed("y"));
};

InteractionModelTestCase.prototype.testIsZoomed_updateOptions_x = function() {
  var g = new Dygraph(document.getElementById("graph"), data2, {});

  g.updateOptions({dateWindow: [-.5, .3]});
  assertTrue(g.isZoomed());
  assertTrue(g.isZoomed("x"));
  assertFalse(g.isZoomed("y"));
};

InteractionModelTestCase.prototype.testIsZoomed_updateOptions_y = function() {
  var g = new Dygraph(document.getElementById("graph"), data2, {});

  g.updateOptions({valueRange: [1, 10]});

  assertTrue(g.isZoomed());
  assertFalse(g.isZoomed("x"));
  assertTrue(g.isZoomed("y"));
};

InteractionModelTestCase.prototype.testIsZoomed_updateOptions_both = function() {
  var g = new Dygraph(document.getElementById("graph"), data2, {});

  g.updateOptions({dateWindow: [-1, 1], valueRange: [1, 10]});

  assertTrue(g.isZoomed());
  assertTrue(g.isZoomed("x"));
  assertTrue(g.isZoomed("y"));
};


InteractionModelTestCase.prototype.testCorrectAxisValueRangeAfterUnzoom = function() {
  var g = new Dygraph(document.getElementById("graph"),
      data2, {
        valueRange: [1, 50],
        dateWindow: [1, 9],
        animatedZooms:false
      });
  
  // Zoom x axis
  DygraphOps.dispatchMouseDown_Point(g, 100, 100);
  DygraphOps.dispatchMouseMove_Point(g, 130, 100);
  DygraphOps.dispatchMouseUp_Point(g, 130, 100);

  // Zoom y axis
  DygraphOps.dispatchMouseDown_Point(g, 100, 100);
  DygraphOps.dispatchMouseMove_Point(g, 100, 130);
  DygraphOps.dispatchMouseUp_Point(g, 100, 130);
  currentYAxisRange = g.yAxisRange();
  currentXAxisRange = g.xAxisRange();
  
  //check that the range for the axis has changed
  assertNotEquals(1, currentXAxisRange[0]);
  assertNotEquals(10, currentXAxisRange[1]);
  assertNotEquals(1, currentYAxisRange[0]);
  assertNotEquals(50, currentYAxisRange[1]);
  
  // unzoom by doubleclick.  This is really the order in which a browser
  // generates events, and we depend on it.
  DygraphOps.dispatchMouseDown_Point(g, 10, 10);
  DygraphOps.dispatchMouseUp_Point(g, 10, 10);
  DygraphOps.dispatchMouseDown_Point(g, 10, 10);
  DygraphOps.dispatchMouseUp_Point(g, 10, 10);
  DygraphOps.dispatchDoubleClick(g, null);
  
  // check if range for y-axis was reset to original value 
  // TODO check if range for x-axis is correct. 
  // Currently not possible because dateRange is set to null and extremes are returned
  newYAxisRange = g.yAxisRange();
  assertEquals(1, newYAxisRange[0]);
  assertEquals(50, newYAxisRange[1]);
};

/**
 * Ensures pointClickCallback is called when some points along the y-axis don't
 * exist.
 */
InteractionModelTestCase.prototype.testPointClickCallback_missingData = function() {

  // There's a B-value at 2, but no A-value.
  var data =
    "X,A,B\n" +
    "1,,100\n"+
    "2,,110\n"+
    "3,140,120\n"+
    "4,130,110\n"+
    "";

  var clicked;
  var g = new Dygraph(document.getElementById("graph"), data, {
    pointClickCallback : function(event, point) {
      clicked = point;
    }
  });

  InteractionModelTestCase.clickAt(g, 2, 110);

  assertEquals(2, clicked.xval);
  assertEquals(110, clicked.yval);
};
