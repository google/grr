/** 
 * @fileoverview Utility functions for Dygraphs.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
var Util = {};

/**
 * Get the y-labels for a given axis.
 *
 * You can specify a parent if more than one graph is in the document.
 */
Util.getYLabels = function(axis_num, parent) {
  axis_num = axis_num || "";
  parent = parent || document;
  var y_labels = parent.getElementsByClassName("dygraph-axis-label-y" + axis_num);
  var ary = [];
  for (var i = 0; i < y_labels.length; i++) {
    ary.push(y_labels[i].innerHTML.replace(/&#160;|&nbsp;/g, ' '));
  }
  return ary;
};

/**
 * Get the x-labels for a given axis.
 *
 * You can specify a parent if more than one graph is in the document.
 */
Util.getXLabels = function(parent) {
  parent = parent || document;
  var x_labels = parent.getElementsByClassName("dygraph-axis-label-x");
  var ary = [];
  for (var i = 0; i < x_labels.length; i++) {
    ary.push(x_labels[i].innerHTML.replace(/&#160;|&nbsp;/g, ' '));
  }
  return ary;
};

/**
 * Returns all text in tags w/ a given css class, sorted.
 * You can specify a parent if more than one graph is on the document.
 */
Util.getClassTexts = function(css_class, parent) {
  parent = parent || document;
  var texts = [];
  var els = parent.getElementsByClassName(css_class);
  for (var i = 0; i < els.length; i++) {
    texts[i] = els[i].textContent;
  }
  texts.sort();
  return texts;
};

Util.getLegend = function(parent) {
  parent = parent || document;
  var legend = parent.getElementsByClassName("dygraph-legend")[0];
  var re = new RegExp(String.fromCharCode(160), 'g');
  return legend.textContent.replace(re, ' ');
};

/**
 * Assert that all elements have a certain style property.
 */
Util.assertStyleOfChildren = function(selector, property, expectedValue) {
  assertTrue(selector.length > 0);
  $.each(selector, function(idx, child) {
    assertEquals(expectedValue,  $(child).css(property));
  });
};


/**
 * Takes in an array of strings and returns an array of floats.
 */
Util.makeNumbers = function(ary) {
  var ret = [];
  for (var i = 0; i < ary.length; i++) {
    ret.push(parseFloat(ary[i]));
  }
  return ret;
};


/**
 * Sample a pixel from the canvas.
 * Returns an [r, g, b, a] tuple where each values is in [0, 255].
 */
Util.samplePixel = function(canvas, x, y) {
  var ctx = canvas.getContext("2d");  // bypasses Proxy if applied.

  // TODO(danvk): Any performance issues with this?
  var imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

  var scale = Dygraph.getContextPixelRatio(ctx);

  var i = 4 * (x * scale + imageData.width * y * scale);
  var d = imageData.data;
  return [d[i], d[i+1], d[i+2], d[i+3]];
};

/**
 * Overrides the browser's built-in XMLHttpRequest with a mock.
 * Usage:
 *
 * var mockXhr = Util.overrideXMLHttpRequest(your_data);
 * ... call code that does an XHR ...
 * mockXhr.respond();  // restores default behavior.
 * ... do your assertions ...
 */
Util.overrideXMLHttpRequest = function(data) {
  var originalXMLHttpRequest = XMLHttpRequest;

  var requests = [];
  var FakeXMLHttpRequest = function () {
    requests.push(this);
  };
  FakeXMLHttpRequest.prototype.open = function () {};
  FakeXMLHttpRequest.prototype.send = function () {
    this.readyState = 4;
    this.status = 200;
    this.responseText = data;
  };
  FakeXMLHttpRequest.restore = function() {
    XMLHttpRequest = originalXMLHttpRequest;
  };
  FakeXMLHttpRequest.respond = function() {
    for (var i = 0; i < requests.length; i++) {
      requests[i].onreadystatechange();
    }
    FakeXMLHttpRequest.restore();
  };
  XMLHttpRequest = FakeXMLHttpRequest;
  return FakeXMLHttpRequest;
};

/**
 * Format a date as 2000/01/23
 * @param {number} dateMillis Millis since epoch.
 * @return {string} The date formatted as YYYY-MM-DD.
 */
Util.formatDate = function(dateMillis) {
  return Dygraph.dateString_(dateMillis).slice(0, 10);  // 10 == "YYYY/MM/DD".length
};
