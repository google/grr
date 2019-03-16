// Copyright (c) 2013 Google, Inc.
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

/*global Dygraph:false */

/**
 * @fileoverview Plug-in for providing unzoom-on-hover.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
Dygraph.Plugins.Unzoom = (function() {

  "use strict";

  /**
   * Create a new instance.
   *
   * @constructor
   */
  var unzoom = function() {
    this.button_ = null;

    // True when the mouse is over the canvas. Must be tracked
    // because the unzoom button state can change even when the
    // mouse-over state hasn't.
    this.over_ = false;
  };

  unzoom.prototype.toString = function() {
    return 'Unzoom Plugin';
  };

  unzoom.prototype.activate = function(g) {
    return {
      willDrawChart: this.willDrawChart
    };
  };

  unzoom.prototype.willDrawChart = function(e) {
    var g = e.dygraph;

    if (this.button_ !== null) {
      // short-circuit: show the button only when we're moused over, and zoomed in.
      var showButton = g.isZoomed() && this.over_;
      this.show(showButton);
      return;
    }

    this.button_ = document.createElement('button');
    this.button_.innerHTML = 'Reset Zoom';
    this.button_.style.display = 'none';
    this.button_.style.position = 'absolute';
    var area = g.plotter_.area;
    this.button_.style.top = (area.y + 4) + 'px';
    this.button_.style.left = (area.x + 4) + 'px';
    this.button_.style.zIndex = 11;
    var parent = g.graphDiv;
    parent.insertBefore(this.button_, parent.firstChild);

    var self = this;
    this.button_.onclick = function() {
      g.resetZoom();
    };

    g.addAndTrackEvent(parent, 'mouseover', function() {
      if (g.isZoomed()) {
        self.show(true);
      }
      self.over_ = true;
    });

    g.addAndTrackEvent(parent, 'mouseout', function() {
      self.show(false);
      self.over_ = false;
    });
  };

  unzoom.prototype.show = function(enabled) {
    this.button_.style.display = enabled ? '' : 'none';
  };

  unzoom.prototype.destroy = function() {
    this.button_.parentElement.removeChild(this.button_);
  };

  return unzoom;

})();
