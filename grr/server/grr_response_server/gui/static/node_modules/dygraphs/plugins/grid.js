/**
 * @license
 * Copyright 2012 Dan Vanderkam (danvdk@gmail.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */
/*global Dygraph:false */

Dygraph.Plugins.Grid = (function() {

/*

Current bits of jankiness:
- Direct layout access
- Direct area access

*/

"use strict";


/**
 * Draws the gridlines, i.e. the gray horizontal & vertical lines running the
 * length of the chart.
 *
 * @constructor
 */
var grid = function() {
};

grid.prototype.toString = function() {
  return "Gridline Plugin";
};

grid.prototype.activate = function(g) {
  return {
    willDrawChart: this.willDrawChart
  };
};

grid.prototype.willDrawChart = function(e) {
  // Draw the new X/Y grid. Lines appear crisper when pixels are rounded to
  // half-integers. This prevents them from drawing in two rows/cols.
  var g = e.dygraph;
  var ctx = e.drawingContext;
  var layout = g.layout_;
  var area = e.dygraph.plotter_.area;

  function halfUp(x)  { return Math.round(x) + 0.5; }
  function halfDown(y){ return Math.round(y) - 0.5; }

  var x, y, i, ticks;
  if (g.getOptionForAxis('drawGrid', 'y')) {
    var axes = ["y", "y2"];
    var strokeStyles = [], lineWidths = [], drawGrid = [], stroking = [], strokePattern = [];
    for (var i = 0; i < axes.length; i++) {
      drawGrid[i] = g.getOptionForAxis('drawGrid', axes[i]);
      if (drawGrid[i]) {
        strokeStyles[i] = g.getOptionForAxis('gridLineColor', axes[i]);
        lineWidths[i] = g.getOptionForAxis('gridLineWidth', axes[i]);
        strokePattern[i] = g.getOptionForAxis('gridLinePattern', axes[i]);
        stroking[i] = strokePattern[i] && (strokePattern[i].length >= 2);
      }
    }
    ticks = layout.yticks;
    ctx.save();
    // draw grids for the different y axes
    for (i = 0; i < ticks.length; i++) {
      var axis = ticks[i][0];
      if(drawGrid[axis]) {
        if (stroking[axis]) {
          ctx.installPattern(strokePattern[axis]);
        }
        ctx.strokeStyle = strokeStyles[axis];
        ctx.lineWidth = lineWidths[axis];

        x = halfUp(area.x);
        y = halfDown(area.y + ticks[i][1] * area.h);
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + area.w, y);
        ctx.closePath();
        ctx.stroke();

        if (stroking[axis]) {
          ctx.uninstallPattern();
        }
      }
    }
    ctx.restore();
  }

  // draw grid for x axis
  if (g.getOptionForAxis('drawGrid', 'x')) {
    ticks = layout.xticks;
    ctx.save();
    var strokePattern = g.getOptionForAxis('gridLinePattern', 'x');
    var stroking = strokePattern && (strokePattern.length >= 2);
    if (stroking) {
      ctx.installPattern(strokePattern);
    }
    ctx.strokeStyle = g.getOptionForAxis('gridLineColor', 'x');
    ctx.lineWidth = g.getOptionForAxis('gridLineWidth', 'x');
    for (i = 0; i < ticks.length; i++) {
      x = halfUp(area.x + ticks[i][0] * area.w);
      y = halfDown(area.y + area.h);
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x, area.y);
      ctx.closePath();
      ctx.stroke();
    }
    if (stroking) {
      ctx.uninstallPattern();
    }
    ctx.restore();
  }
};

grid.prototype.destroy = function() {
};

return grid;

})();
