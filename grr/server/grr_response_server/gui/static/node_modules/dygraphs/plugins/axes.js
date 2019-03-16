/**
 * @license
 * Copyright 2012 Dan Vanderkam (danvdk@gmail.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */

/*global Dygraph:false */

Dygraph.Plugins.Axes = (function() {

'use strict';

/*
Bits of jankiness:
- Direct layout access
- Direct area access
- Should include calculation of ticks, not just the drawing.

Options left to make axis-friendly.
  ('drawAxesAtZero')
  ('xAxisHeight')
*/

/**
 * Draws the axes. This includes the labels on the x- and y-axes, as well
 * as the tick marks on the axes.
 * It does _not_ draw the grid lines which span the entire chart.
 */
var axes = function() {
  this.xlabels_ = [];
  this.ylabels_ = [];
};

axes.prototype.toString = function() {
  return 'Axes Plugin';
};

axes.prototype.activate = function(g) {
  return {
    layout: this.layout,
    clearChart: this.clearChart,
    willDrawChart: this.willDrawChart
  };
};

axes.prototype.layout = function(e) {
  var g = e.dygraph;

  if (g.getOptionForAxis('drawAxis', 'y')) {
    var w = g.getOptionForAxis('axisLabelWidth', 'y') + 2 * g.getOptionForAxis('axisTickSize', 'y');
    e.reserveSpaceLeft(w);
  }

  if (g.getOptionForAxis('drawAxis', 'x')) {
    var h;
    // NOTE: I think this is probably broken now, since g.getOption() now
    // hits the dictionary. (That is, g.getOption('xAxisHeight') now always
    // has a value.)
    if (g.getOption('xAxisHeight')) {
      h = g.getOption('xAxisHeight');
    } else {
      h = g.getOptionForAxis('axisLabelFontSize', 'x') + 2 * g.getOptionForAxis('axisTickSize', 'x');
    }
    e.reserveSpaceBottom(h);
  }

  if (g.numAxes() == 2) {
    if (g.getOptionForAxis('drawAxis', 'y2')) {
      var w = g.getOptionForAxis('axisLabelWidth', 'y2') + 2 * g.getOptionForAxis('axisTickSize', 'y2');
      e.reserveSpaceRight(w);
    }
  } else if (g.numAxes() > 2) {
    g.error('Only two y-axes are supported at this time. (Trying ' +
            'to use ' + g.numAxes() + ')');
  }
};

axes.prototype.detachLabels = function() {
  function removeArray(ary) {
    for (var i = 0; i < ary.length; i++) {
      var el = ary[i];
      if (el.parentNode) el.parentNode.removeChild(el);
    }
  }

  removeArray(this.xlabels_);
  removeArray(this.ylabels_);
  this.xlabels_ = [];
  this.ylabels_ = [];
};

axes.prototype.clearChart = function(e) {
  this.detachLabels();
};

axes.prototype.willDrawChart = function(e) {
  var g = e.dygraph;

  if (!g.getOptionForAxis('drawAxis', 'x') &&
      !g.getOptionForAxis('drawAxis', 'y') &&
      !g.getOptionForAxis('drawAxis', 'y2')) {
    return;
  }
  
  // Round pixels to half-integer boundaries for crisper drawing.
  function halfUp(x)  { return Math.round(x) + 0.5; }
  function halfDown(y){ return Math.round(y) - 0.5; }

  var context = e.drawingContext;
  var containerDiv = e.canvas.parentNode;
  var canvasWidth = g.width_;  // e.canvas.width is affected by pixel ratio.
  var canvasHeight = g.height_;

  var label, x, y, tick, i;

  var makeLabelStyle = function(axis) {
    return {
      position: 'absolute',
      fontSize: g.getOptionForAxis('axisLabelFontSize', axis) + 'px',
      zIndex: 10,
      color: g.getOptionForAxis('axisLabelColor', axis),
      width: g.getOptionForAxis('axisLabelWidth', axis) + 'px',
      // height: g.getOptionForAxis('axisLabelFontSize', 'x') + 2 + "px",
      lineHeight: 'normal',  // Something other than "normal" line-height screws up label positioning.
      overflow: 'hidden'
    };
  };

  var labelStyles = {
    x : makeLabelStyle('x'),
    y : makeLabelStyle('y'),
    y2 : makeLabelStyle('y2')
  };

  var makeDiv = function(txt, axis, prec_axis) {
    /*
     * This seems to be called with the following three sets of axis/prec_axis:
     * x: undefined
     * y: y1
     * y: y2
     */
    var div = document.createElement('div');
    var labelStyle = labelStyles[prec_axis == 'y2' ? 'y2' : axis];
    for (var name in labelStyle) {
      if (labelStyle.hasOwnProperty(name)) {
        div.style[name] = labelStyle[name];
      }
    }
    var inner_div = document.createElement('div');
    inner_div.className = 'dygraph-axis-label' +
                          ' dygraph-axis-label-' + axis +
                          (prec_axis ? ' dygraph-axis-label-' + prec_axis : '');
    inner_div.innerHTML = txt;
    div.appendChild(inner_div);
    return div;
  };

  // axis lines
  context.save();

  var layout = g.layout_;
  var area = e.dygraph.plotter_.area;

  // Helper for repeated axis-option accesses.
  var makeOptionGetter = function(axis) {
    return function(option) {
      return g.getOptionForAxis(option, axis);
    };
  };

  if (g.getOptionForAxis('drawAxis', 'y')) {
    if (layout.yticks && layout.yticks.length > 0) {
      var num_axes = g.numAxes();
      var getOptions = [makeOptionGetter('y'), makeOptionGetter('y2')];
      for (i = 0; i < layout.yticks.length; i++) {
        tick = layout.yticks[i];
        if (typeof(tick) == 'function') return;  // <-- when would this happen?
        x = area.x;
        var sgn = 1;
        var prec_axis = 'y1';
        var getAxisOption = getOptions[0];
        if (tick[0] == 1) {  // right-side y-axis
          x = area.x + area.w;
          sgn = -1;
          prec_axis = 'y2';
          getAxisOption = getOptions[1];
        }
        var fontSize = getAxisOption('axisLabelFontSize');
        y = area.y + tick[1] * area.h;

        /* Tick marks are currently clipped, so don't bother drawing them.
        context.beginPath();
        context.moveTo(halfUp(x), halfDown(y));
        context.lineTo(halfUp(x - sgn * this.attr_('axisTickSize')), halfDown(y));
        context.closePath();
        context.stroke();
        */

        label = makeDiv(tick[2], 'y', num_axes == 2 ? prec_axis : null);
        var top = (y - fontSize / 2);
        if (top < 0) top = 0;

        if (top + fontSize + 3 > canvasHeight) {
          label.style.bottom = '0';
        } else {
          label.style.top = top + 'px';
        }
        if (tick[0] === 0) {
          label.style.left = (area.x - getAxisOption('axisLabelWidth') - getAxisOption('axisTickSize')) + 'px';
          label.style.textAlign = 'right';
        } else if (tick[0] == 1) {
          label.style.left = (area.x + area.w +
                              getAxisOption('axisTickSize')) + 'px';
          label.style.textAlign = 'left';
        }
        label.style.width = getAxisOption('axisLabelWidth') + 'px';
        containerDiv.appendChild(label);
        this.ylabels_.push(label);
      }

      // The lowest tick on the y-axis often overlaps with the leftmost
      // tick on the x-axis. Shift the bottom tick up a little bit to
      // compensate if necessary.
      var bottomTick = this.ylabels_[0];
      // Interested in the y2 axis also?
      var fontSize = g.getOptionForAxis('axisLabelFontSize', 'y');
      var bottom = parseInt(bottomTick.style.top, 10) + fontSize;
      if (bottom > canvasHeight - fontSize) {
        bottomTick.style.top = (parseInt(bottomTick.style.top, 10) -
            fontSize / 2) + 'px';
      }
    }

    // draw a vertical line on the left to separate the chart from the labels.
    var axisX;
    if (g.getOption('drawAxesAtZero')) {
      var r = g.toPercentXCoord(0);
      if (r > 1 || r < 0 || isNaN(r)) r = 0;
      axisX = halfUp(area.x + r * area.w);
    } else {
      axisX = halfUp(area.x);
    }

    context.strokeStyle = g.getOptionForAxis('axisLineColor', 'y');
    context.lineWidth = g.getOptionForAxis('axisLineWidth', 'y');

    context.beginPath();
    context.moveTo(axisX, halfDown(area.y));
    context.lineTo(axisX, halfDown(area.y + area.h));
    context.closePath();
    context.stroke();

    // if there's a secondary y-axis, draw a vertical line for that, too.
    if (g.numAxes() == 2) {
      context.strokeStyle = g.getOptionForAxis('axisLineColor', 'y2');
      context.lineWidth = g.getOptionForAxis('axisLineWidth', 'y2');
      context.beginPath();
      context.moveTo(halfDown(area.x + area.w), halfDown(area.y));
      context.lineTo(halfDown(area.x + area.w), halfDown(area.y + area.h));
      context.closePath();
      context.stroke();
    }
  }

  if (g.getOptionForAxis('drawAxis', 'x')) {
    if (layout.xticks) {
      var getAxisOption = makeOptionGetter('x');
      for (i = 0; i < layout.xticks.length; i++) {
        tick = layout.xticks[i];
        x = area.x + tick[0] * area.w;
        y = area.y + area.h;

        /* Tick marks are currently clipped, so don't bother drawing them.
        context.beginPath();
        context.moveTo(halfUp(x), halfDown(y));
        context.lineTo(halfUp(x), halfDown(y + this.attr_('axisTickSize')));
        context.closePath();
        context.stroke();
        */

        label = makeDiv(tick[1], 'x');
        label.style.textAlign = 'center';
        label.style.top = (y + getAxisOption('axisTickSize')) + 'px';

        var left = (x - getAxisOption('axisLabelWidth')/2);
        if (left + getAxisOption('axisLabelWidth') > canvasWidth) {
          left = canvasWidth - getAxisOption('axisLabelWidth');
          label.style.textAlign = 'right';
        }
        if (left < 0) {
          left = 0;
          label.style.textAlign = 'left';
        }

        label.style.left = left + 'px';
        label.style.width = getAxisOption('axisLabelWidth') + 'px';
        containerDiv.appendChild(label);
        this.xlabels_.push(label);
      }
    }

    context.strokeStyle = g.getOptionForAxis('axisLineColor', 'x');
    context.lineWidth = g.getOptionForAxis('axisLineWidth', 'x');
    context.beginPath();
    var axisY;
    if (g.getOption('drawAxesAtZero')) {
      var r = g.toPercentYCoord(0, 0);
      if (r > 1 || r < 0) r = 1;
      axisY = halfDown(area.y + r * area.h);
    } else {
      axisY = halfDown(area.y + area.h);
    }
    context.moveTo(halfUp(area.x), axisY);
    context.lineTo(halfUp(area.x + area.w), axisY);
    context.closePath();
    context.stroke();
  }

  context.restore();
};

return axes;
})();
