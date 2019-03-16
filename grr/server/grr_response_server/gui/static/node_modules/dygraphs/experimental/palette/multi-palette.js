// Copyright (c) 2011 Google, Inc.
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
 * @fileoverview Multiple Dygraphs palettes, grouped by global, series, etc..
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */

function MultiPalette() {
  this.palettes = {};
  this.root = null;
  this.filterBar = null;
  // This is meant to be overridden by a palette host.
  this.activePalette = null;
  this.onchange = function() {};
}

MultiPalette.optionSetValues = {
  "global": "global",
  "x": "x axis",
  "y": "y axis",
  "y2": "y2 axis",  
};

MultiPalette.prototype.create = function(parentElement) {
  var self = this;

  this.root = $("<div>").addClass("palette").appendTo(parentElement);
  var header = $("<div>").addClass("header").appendTo(this.root);
  // Selector for series and axes.
  var selectorRow = $("<div>").appendTo(header);
  this.optionSelector = $("<select>")
      .change(function(x) {
        self.activate(self.optionSelector.val());
      });

  selectorRow
      .append($("<span>").text("Option Set:"))
      .append(this.optionSelector)
       .append($("<span>")
          .append($("<a>")
              .addClass("link")
              .text("to hash")
              .css("float", "right")
              .css("padding-right", "8px")
              .click(function() { self.showHash(); })));

  var filter = function() {
    $.each(self.palettes, function(key, value) {
      value.filter(self.filterBar.val());
    });
  }

  this.filterBar = $("<input>", { type : "search" })
      .keyup(filter)
      .click(filter);

  header.append($("<div>")
      .append($("<span>").text("Filter:"))
      .append($("<span>").append(this.filterBar))
      .append($("<span>")
          .append($("<a>")
              .addClass("link")
              .text("Redraw")
              .css("float", "right")
              .css("padding-right", "8px")
              .click(function() { self.onchange(); }))));

  $.each(MultiPalette.optionSetValues, function(key, value) {
    self.createPalette_(key, key, value);
  });

  this.activate("global");
}

MultiPalette.prototype.createPalette_ = function(key, scope, value) {
   this.optionSelector
     .append($("<option></option>")
     .attr("value", key)
     .text(value)); 
  var palette = new Palette(scope);
  palette.create(this.root);
  palette.root.hide();
  var self = this;
  palette.onchange = function() {
    self.onchange();
  };
  this.palettes[key] = palette;
}

MultiPalette.prototype.setSeries = function(labels) {
  for (var idx = 1; idx < labels.length; idx++) {
    this.conditionallyAddSingleSeries_(labels[idx]);
  }
}

MultiPalette.prototype.conditionallyAddSingleSeries_ = function(series) {
  var key = "series:" + series;
  if (!this.palettes.hasOwnProperty(key)) {
    this.createPalette_(key, "series", series + " (series)");
  }
}

MultiPalette.prototype.activate = function(key) {
  if (this.activePalette) {
    this.activePalette.root.hide();
  }
  this.activePalette = this.palettes[key];
  this.activePalette.root.show();
}

MultiPalette.prototype.showHash = function() {
  var hash = this.read();
  var textarea = new TextArea();

  var hashToString = function(hash) {
    /*
     * JSON.stringify isn't built to be nice to functions. The following fixes
     * this.
     *
     * First, val.toString only does part of the work, turning it into
     * "function () {\n  alert(\"p-click!\");\n}",
     *
     * {start,end}Marker make the surrounding quotes easy to find, and then
     * remove them. It also converts the instances of \n and \" so the
     * result looks like:
     * function () {
     *   alert("p-click!");
     * }",
     */
    var startMarker = "<~%!<";
    var endMarker = ">!%~>";
    var replacer = function(key, val) {
      if (typeof val === 'function') {
        return startMarker + val.toString() + endMarker;
      }
      return val;
    }
    var text = JSON.stringify(hash, replacer, 2);
    while(true) {
      var start = text.indexOf(startMarker);
      var end = text.indexOf(endMarker); 
      if (start == -1) {
        break;
      }
      var substring = text.substring(start + startMarker.length, end);
      while(substring.indexOf("\\n") >= 0) {
        substring = substring.replace("\\n", "\n");
      }
      while(substring.indexOf("\\\"") >= 0) {
        substring = substring.replace("\\\"", "\"");
      }
      text = text.substring(0, start - 1)
          + substring
          + text.substring(end + endMarker.length + 1);
    }
    return text;
  }

  var text = hashToString(hash);
  var self = this;
  textarea.show("options", text);
  textarea.okCallback = function(value) {
    if (value != text) {
      var newHash;
      eval("newHash = " + value + ";");
      self.write(newHash);
      self.onchange();
    }
  };
}

/**
 * Read from palette
 */
MultiPalette.prototype.read = function() {
  var results = this.palettes.global.read();
  results.axes = {};
  results.series = {};
  var clearIfEmpty = function(hash, key) {
    var val = hash[key];
    if ($.isEmptyObject(val)) {
      delete hash[key];
    }
  }
  var clearEmptyChildren = function(hash) {
    for (var key in hash) {
      if (hash.hasOwnProperty(key)) {
        clearIfEmpty(hash, key);
      }
    }
  }

  results.axes.x = this.palettes.x.read();
  results.axes.y = this.palettes.y.read();
  results.axes.y2 = this.palettes.y2.read();

  clearEmptyChildren(results.axes);
  clearIfEmpty(results, "axes");

  for (var key in this.palettes) {
    if (key.indexOf("series:") == 0) {
      var series = key.substring("series:".length);
      results.series[series] = this.palettes[key].read();
    }
  }

  clearEmptyChildren(results.series);
  clearIfEmpty(results, "series");

  return results;
}

/**
 * Write to palette from hash.
 */
MultiPalette.prototype.write = function(hash) {
  this.palettes.global.write(hash);
  if (hash.hasOwnProperty("axes")) {
    var axes = hash.axes;
    this.palettes.x.write(axes["x"]);
    this.palettes.y.write(axes["y"]);
    this.palettes.y2.write(axes["y2"]);
  }

  if (hash.hasOwnProperty("series")) {
    for (var key in hash.series) {
      if (hash.series.hasOwnProperty(key)) {
        this.conditionallyAddSingleSeries_(key);
        this.palettes["series:" + key].write(hash.series[key]);
      }
    }
  }  
}
