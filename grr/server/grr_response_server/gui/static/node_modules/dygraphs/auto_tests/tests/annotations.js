/**
 * @fileoverview Tests relating to annotations
 *
 * @author danvk@google.com (Dan Vanderkam)
 */
var AnnotationsTestCase = TestCase("annotations");

AnnotationsTestCase.prototype.setUp = function() {
  document.body.innerHTML = "<div id='graph'></div>";
};

AnnotationsTestCase.prototype.tearDown = function() {
};

AnnotationsTestCase.prototype.testAnnotationsDrawn = function() {
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
  g.setAnnotations([
    {
      series: 'Y',
      x: 1,
      shortText: 'A',
      text: 'Long A',
      cssClass: 'ann1'
    },
    {
      series: 'Y',
      x: 2,
      shortText: 'B',
      text: 'Long B',
      cssClass: 'ann2'
    }
  ]);

  assertEquals(2, g.annotations().length);
  var a1 = document.getElementsByClassName('ann1');
  assertEquals(1, a1.length);
  a1 = a1[0];
  assertEquals('A', a1.textContent);

  var a2 = document.getElementsByClassName('ann2');
  assertEquals(1, a2.length);
  a2 = a2[0];
  assertEquals('B', a2.textContent);
};

// Some errors that should be flagged:
// 1. Invalid series name (e.g. 'X' or 'non-existent')
// 2. Passing a string as 'x' instead of a number (e.g. x: '1')

AnnotationsTestCase.prototype.testAnnotationsDontDisappearOnResize = function() {
  var opts = {
  };
  var data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  g.setAnnotations([
    {
      series: 'Y',
      x: 1,
      shortText: 'A',
      text: 'Long A',
      cssClass: 'ann1'
    }
  ]);

  // Check that it displays at all
  assertEquals(1, g.annotations().length);
  var a1 = document.getElementsByClassName('ann1');
  assertEquals(1, a1.length);
  a1 = a1[0];
  assertEquals('A', a1.textContent);

  // ... and that resizing doesn't kill it.
  g.resize(400, 300);
  assertEquals(1, g.annotations().length);
  var a1 = document.getElementsByClassName('ann1');
  assertEquals(1, a1.length);
  a1 = a1[0];
  assertEquals('A', a1.textContent);
};

// Verify that annotations outside of the visible x-range are not shown.
AnnotationsTestCase.prototype.testAnnotationsOutOfRangeX = function() {
  var opts = {
  };
  var data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  g.setAnnotations([
    {
      series: 'Y',
      x: 1,
      shortText: 'A',
      text: 'Long A',
      cssClass: 'ann1'
    }
  ]);

  // Check that it displays at all
  assertEquals(1, g.annotations().length);
  var a1 = document.getElementsByClassName('ann1');
  assertEquals(1, a1.length);
  a1 = a1[0];
  assertEquals('A', a1.textContent);

  // ... and that panning right removes the annotation.
  g.updateOptions({dateWindow: [2, 6]});
  assertEquals(1, g.annotations().length);
  a1 = document.getElementsByClassName('ann1');
  assertEquals(0, a1.length);

  // ... and that panning left brings it back.
  g.updateOptions({dateWindow: [0, 4]});
  assertEquals(1, g.annotations().length);
  a1 = document.getElementsByClassName('ann1');
  assertEquals(1, a1.length);
};

// Verify that annotations outside of the visible y-range are not shown.
AnnotationsTestCase.prototype.testAnnotationsOutOfRangeY = function() {
  var opts = {
  };
  var data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n" +
      "3,0\n"
  ;

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, data, opts);
  g.setAnnotations([
    {
      series: 'Y',
      x: 1,
      shortText: 'A',
      text: 'Long A',
      cssClass: 'ann1'
    }
  ]);

  // ... check that panning up removes the annotation.
  g.updateOptions({valueRange: [0.5, 2.5]});
  assertEquals(1, g.annotations().length);
  a1 = document.getElementsByClassName('ann1');
  assertEquals(0, a1.length);

  // ... and that panning down brings it back.
  g.updateOptions({valueRange: [-1, 1]});
  assertEquals(1, g.annotations().length);
  a1 = document.getElementsByClassName('ann1');
  assertEquals(1, a1.length);
};

AnnotationsTestCase.prototype.testAnnotationsDrawnInDrawCallback = function() {
  var data = "X,Y\n" +
      "0,-1\n" +
      "1,0\n" +
      "2,1\n";

  var graph = document.getElementById("graph");

  var calls = [];
  var g = new Dygraph(graph, data, {
      width: 480,
      height: 320,
      drawCallback: function(g, initial) {
        calls.push(initial);
        if (initial) {
          g.setAnnotations([
            {
              series: 'Y',
              x: 1,
              shortText: 'A',
              text: 'Long A',
            },
          ]);
        }
      }
    });

  assertEquals([true, false], calls);
};


// Test that annotations on the same point are stacked.
// Regression test for http://code.google.com/p/dygraphs/issues/detail?id=256
AnnotationsTestCase.prototype.testAnnotationsStacked = function() {
  var data = 'X,Y1,Y2\n' +
      '0,1,2\n' +
      '1,2,3\n';
  var graph = document.getElementById("graph");
  var annotations = [
    {
      series: 'Y1',
      x: 0,
      shortText: '1',
      attachAtBottom: true
    },
    {
      series: 'Y2',
      x: 0,
      shortText: '2',
      attachAtBottom: true
    }
  ];
  var g = new Dygraph(graph, data, {
    width: 480,
    height: 320
  });
  g.setAnnotations(annotations);

  var annEls = document.getElementsByClassName('dygraphDefaultAnnotation');
  assertEquals(2, annEls.length);

  assertEquals(annEls[0].offsetLeft, annEls[1].offsetLeft);
  assert(annEls[1].offsetTop < annEls[0].offsetTop - 10);
};


// Test the .ready() method, which is most often used with setAnnotations().
AnnotationsTestCase.prototype.testReady = function() {
  var data = 'X,Y1,Y2\n' +
      '0,1,2\n' +
      '1,2,3\n';
  var mockXhr = Util.overrideXMLHttpRequest(data);

  var graph = document.getElementById("graph");
  var g = new Dygraph(graph, "data.csv", {
    width: 480,
    height: 320
  });

  var ready_calls = 0;
  g.ready(function() { ready_calls++; });

  assertEquals(0, ready_calls);
  mockXhr.respond();
  assertEquals(1, ready_calls);

  // Make sure that ready isn't called on redraws.
  g.updateOptions({});
  assertEquals(1, ready_calls);

  // Or data changes.
  g.updateOptions({file: data});
  assertEquals(1, ready_calls);
};
