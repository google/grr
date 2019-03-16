// Copyright 2011 Google Inc. All Rights Reserved.

/**
 * @fileoverview Regression test based on an optimization w/
 * unforeseen consequences.
 * @author danvk@google.com (Dan Vanderkam)
 */

var SelectionTestCase = TestCase("selection");

SelectionTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

SelectionTestCase.prototype.testSetGetSelection = function() {
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph,
    "X,Y\n" +
    "1,1\n" +
    "50,50\n" +
    "100,100\n"
  );

  g.setSelection(0);
  assertEquals(0, g.getSelection());
  g.setSelection(1);
  assertEquals(1, g.getSelection());
  g.setSelection(2);
  assertEquals(2, g.getSelection());
};

SelectionTestCase.prototype.testSetGetSelectionDense = function() {
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph,
    "X,Y\n" +
    "1,1\n" +
    "50,50\n" +
    "50.0001,50.0001\n" +
    "100,100\n"
  );

  g.setSelection(0);
  assertEquals(0, g.getSelection());
  g.setSelection(1);
  assertEquals(1, g.getSelection());
  g.setSelection(2);
  assertEquals(2, g.getSelection());
  g.setSelection(3);
  assertEquals(3, g.getSelection());
};

SelectionTestCase.prototype.testSetGetSelectionMissingPoints = function() {
  dataHandler = function() {};
  dataHandler.prototype = new Dygraph.DataHandlers.DefaultHandler();
  dataHandler.prototype.seriesToPoints = function(series, setName, boundaryIdStart) {
    var val = null;
    if (setName == 'A') {
      val = 1;
    } else if (setName == 'B') {
      val = 2;
    } else if (setName == 'C') {
      val = 3;
    }
    return [{
      x: NaN,
      y: NaN,
      xval: val,
      yval: val,
      name: setName,
      idx: val - 1
    }];
  };
  var graph = document.getElementById("graph");
  var g = new Dygraph(graph,
    "X,A,B,C\n" +
    "1,1,null,null\n" +
    "2,null,2,null\n" +
    "3,null,null,3\n",
    {
      dataHandler: dataHandler
    }
  );

  g.setSelection(0);
  assertEquals(0, g.getSelection());
  g.setSelection(1);
  assertEquals(1, g.getSelection());
  g.setSelection(2);
  assertEquals(2, g.getSelection());
};
