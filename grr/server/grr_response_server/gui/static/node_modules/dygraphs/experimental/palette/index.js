// Copyright (c) 2012 Google, Inc.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

/** 
 * @fileoverview Javascript to run index.html.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */

"use strict";

var Index = {};

Index.splitVariables = function() { // http://www.idealog.us/2006/06/javascript_to_p.html
  var query = window.location.search.substring(1); 
  var args = {};
  var vars = query.split("&"); 
  for (var i = 0; i < vars.length; i++) { 
    if (vars[i].length > 0) {
      var pair = vars[i].split("="); 
      args[pair[0]] = pair[1];
    }
  }
  return args;
}

/**
 * Draw the graph.
 * @param {Object} element the display element
 * @param {Object} data the data to be shown
 * @param {Object} options the options hash.
 */
Index.draw = function(element, data, options) {
  element.innerHTML = "";
  element.removeAttribute("style");

  // Replace the drawCallback function with one that also lets us track
  // all labels (for the palette.)
  // If the drawCallback option is not specified, use a null function.
  var originalDraw = options["drawCallback"] || function() {};
  options.drawCallback = function(g, isInitial) {
    Index.palette.setSeries(g.getLabels());
    // Call the original function, too.
    originalDraw(g, isInitial);
  };

  var g = new Dygraph(
    element,
    data,
    options
  );
  
  // These don't work yet.
  g.updateOptions({
    labelsDiv: 'status',
  });
}

Index.addMessage = function(text) {
  var messages = document.getElementById("messages");
  messages.textContent = messages.textContent + text + "\n";
}

/**
 * Start up the palette system.
 */
Index.start = function() {
  var variables = Index.splitVariables();
  var sampleName = variables["sample"] || "interestingShapes";
  var sampleIndex = Samples.indexOf(sampleName);
  var sample = Samples.data[sampleIndex];
  var data = sample.data;
  var redraw = function() {
    Index.draw(document.getElementById("graph"), data, Index.palette.read());
  }

  // Selector is the drop-down for selecting a set of data.

  // Popupate the selector with the set of data samples
  var selector = document.getElementById("selector").getElementsByTagName("select")[0];
  for (var idx in Samples.data) {
    var entry = Samples.data[idx];
    var option = document.createElement("option");
    option.value = entry.id;
    option.textContent = entry.title;
    selector.appendChild(option);
  }
  selector.onchange = function() {
    var id = selector.options[selector.selectedIndex].value;
    var url = document.URL;
    var qmIndex = url.indexOf("?");
    if (qmIndex >= 0) {
      url = url.substring(0, qmIndex);
    }
    url = url + "?sample=" + id;
    for (var idx in variables) {
      if (idx != "sample") {
        url = url + "&" + idx + "=" + variables[idx];
      }
    }
    window.location = url;
  }
  selector.selectedIndex = sampleIndex;

  // Palette contains the widget that builds options.
  Index.palette = new MultiPalette();
  Index.palette.create(document.getElementById("optionsPalette"));
  Index.palette.write(sample.options);
  Index.palette.onchange = redraw;
  Index.palette.filterBar.focus();

  redraw();

  // Find all new options which we don't implement here in the palette.
  for (var opt in Dygraph.OPTIONS_REFERENCE) {
    if (!(opt in opts)) {
      var entry = Dygraph.OPTIONS_REFERENCE[opt];
      console.warn("missing option: " + opt + " of type " + entry.type);
    }
  }
}
