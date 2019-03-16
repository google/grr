/** 
 * @fileoverview Test cases for a graph contained in a scrolling div
 *
 * @author konigsberg@google.com (Robert Konigsbrg)
 */
var ScrollingDivTestCase = TestCase("scrolling-div");

ScrollingDivTestCase.prototype.setUp = function() {

var LOREM_IPSUM =
    "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod\n" +
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,\n" +
    "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo\n" +
    "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse\n" +
    "cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat\n" +
    "non proident, sunt in culpa qui officia deserunt mollit anim id est\n" +
    "laborum.</p>";

  document.body.innerHTML = 
      "<div id='scroller' style='overflow: scroll; height: 450px; width: 800px;'>" +
      "<div id='graph'></div>" +
      "<div style='height:100px; background-color:green;'>" + LOREM_IPSUM + " </div>" +
      "<div style='height:100px; background-color:red;'>" + LOREM_IPSUM + "</div>" +
      "</div>";

  var data = [
      [ 10, 1 ],
      [ 20, 3 ],
      [ 30, 2 ],
      [ 40, 4 ],
      [ 50, 3 ],
      [ 60, 5 ],
      [ 70, 4 ],
      [ 80, 6 ] ];

  var graph = document.getElementById("graph");

  this.point = null;
  var self = this;
  this.g = new Dygraph(graph, data,
          {
            labels : ['a', 'b'],
            drawPoints : true,
            highlightCircleSize : 6,
            pointClickCallback : function(evt, point) {
              self.point = point;
            }
          }
      );
  
};

// This is usually something like 15, but for OS X Lion and its auto-hiding
// scrollbars, it's 0. This is a large enough difference that we need to
// consider it when synthesizing clicks.
// Adapted from http://davidwalsh.name/detect-scrollbar-width
ScrollingDivTestCase.prototype.detectScrollbarWidth = function() {
  // Create the measurement node
  var scrollDiv = document.createElement("div");
  scrollDiv.style.width = "100px";
  scrollDiv.style.height = "100px";
  scrollDiv.style.overflow = "scroll";
  scrollDiv.style.position = "absolute";
  scrollDiv.style.top = "-9999px";
  document.body.appendChild(scrollDiv);

  // Get the scrollbar width
  var scrollbarWidth = scrollDiv.offsetWidth - scrollDiv.clientWidth;

  // Delete the DIV 
  document.body.removeChild(scrollDiv);

  return scrollbarWidth;
};

ScrollingDivTestCase.prototype.tearDown = function() {
};

/**
 * This tests that when the nested div is unscrolled, things work normally.
 */
ScrollingDivTestCase.prototype.testUnscrolledDiv = function() {

  document.getElementById('scroller').scrollTop = 0;

  var clickOn4_40 = {
    clientX: 244,
    clientY: 131,
    screenX: 416,
    screenY: 320
  };

  DygraphOps.dispatchCanvasEvent(this.g, DygraphOps.createEvent(clickOn4_40, { type : 'mousemove' }));
  DygraphOps.dispatchCanvasEvent(this.g, DygraphOps.createEvent(clickOn4_40, { type : 'mousedown' }));
  DygraphOps.dispatchCanvasEvent(this.g, DygraphOps.createEvent(clickOn4_40, { type : 'mouseup' }));

  assertEquals(40, this.point.xval);
  assertEquals(4, this.point.yval);
};

/**
 * This tests that when the nested div is scrolled, things work normally.
 */
ScrollingDivTestCase.prototype.testScrolledDiv = function() {
  document.getElementById('scroller').scrollTop = 117;

  var clickOn4_40 = {
    clientX: 244,
    clientY: 30 - this.detectScrollbarWidth(),
    screenX: 416,
    screenY: 160
  };

  DygraphOps.dispatchCanvasEvent(this.g, DygraphOps.createEvent(clickOn4_40, { type : 'mousemove' }));
  DygraphOps.dispatchCanvasEvent(this.g, DygraphOps.createEvent(clickOn4_40, { type : 'mousedown' }));
  DygraphOps.dispatchCanvasEvent(this.g, DygraphOps.createEvent(clickOn4_40, { type : 'mouseup' }));

  assertEquals(40, this.point.xval);
  assertEquals(4, this.point.yval);
};
