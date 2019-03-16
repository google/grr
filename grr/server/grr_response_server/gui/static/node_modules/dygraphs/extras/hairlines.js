/**
 * @license
 * Copyright 2013 Dan Vanderkam (danvdk@gmail.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 *
 * Note: This plugin requires jQuery and jQuery UI Draggable.
 *
 * See high-level documentation at
 * https://docs.google.com/document/d/1OHNE8BNNmMtFlRQ969DACIYIJ9VVJ7w3dSPRJDEeIew/edit#
 */

/*global Dygraph:false */

Dygraph.Plugins.Hairlines = (function() {

"use strict";

/**
 * @typedef {
 *   xval:  number,      // x-value (i.e. millis or a raw number)
 *   interpolated: bool,  // alternative is to snap to closest
 *   lineDiv: !Element    // vertical hairline div
 *   infoDiv: !Element    // div containing info about the nearest points
 *   selected: boolean    // whether this hairline is selected
 * } Hairline
 */

// We have to wait a few ms after clicks to give the user a chance to
// double-click to unzoom. This sets that delay period.
var CLICK_DELAY_MS = 300;

var hairlines = function(opt_options) {
  /* @type {!Array.<!Hairline>} */
  this.hairlines_ = [];

  // Used to detect resizes (which require the divs to be repositioned).
  this.lastWidth_ = -1;
  this.lastHeight = -1;
  this.dygraph_ = null;

  this.addTimer_ = null;
  opt_options = opt_options || {};

  this.divFiller_ = opt_options['divFiller'] || null;
};

hairlines.prototype.toString = function() {
  return "Hairlines Plugin";
};

hairlines.prototype.activate = function(g) {
  this.dygraph_ = g;
  this.hairlines_ = [];

  return {
    didDrawChart: this.didDrawChart,
    click: this.click,
    dblclick: this.dblclick,
    dataDidUpdate: this.dataDidUpdate
  };
};

hairlines.prototype.detachLabels = function() {
  for (var i = 0; i < this.hairlines_.length; i++) {
    var h = this.hairlines_[i];
    $(h.lineDiv).remove();
    $(h.infoDiv).remove();
    this.hairlines_[i] = null;
  }
  this.hairlines_ = [];
};

hairlines.prototype.hairlineWasDragged = function(h, event, ui) {
  var area = this.dygraph_.getArea();
  var oldXVal = h.xval;
  h.xval = this.dygraph_.toDataXCoord(ui.position.left);
  this.moveHairlineToTop(h);
  this.updateHairlineDivPositions();
  this.updateHairlineInfo();
  this.updateHairlineStyles();
  $(this).triggerHandler('hairlineMoved', {
    oldXVal: oldXVal,
    newXVal: h.xval
  });
  $(this).triggerHandler('hairlinesChanged', {});
};

// This creates the hairline object and returns it.
// It does not position it and does not attach it to the chart.
hairlines.prototype.createHairline = function(props) {
  var h;
  var self = this;

  var $lineContainerDiv = $('<div/>').css({
      'width': '6px',
      'margin-left': '-3px',
      'position': 'absolute',
      'z-index': '10'
    })
    .addClass('dygraph-hairline');

  var $lineDiv = $('<div/>').css({
    'width': '1px',
    'position': 'relative',
    'left': '3px',
    'background': 'black',
    'height': '100%'
  });
  $lineDiv.appendTo($lineContainerDiv);

  var $infoDiv = $('#hairline-template').clone().removeAttr('id').css({
      'position': 'absolute'
    })
    .show();

  // Surely there's a more jQuery-ish way to do this!
  $([$infoDiv.get(0), $lineContainerDiv.get(0)])
    .draggable({
      'axis': 'x',
      'drag': function(event, ui) {
        self.hairlineWasDragged(h, event, ui);
      }
      // TODO(danvk): set cursor here
    });

  h = $.extend({
    interpolated: true,
    selected: false,
    lineDiv: $lineContainerDiv.get(0),
    infoDiv: $infoDiv.get(0)
  }, props);

  var that = this;
  $infoDiv.on('click', '.hairline-kill-button', function(e) {
    that.removeHairline(h);
    $(that).triggerHandler('hairlineDeleted', {
      xval: h.xval
    });
    $(that).triggerHandler('hairlinesChanged', {});
    e.stopPropagation();  // don't want .click() to trigger, below.
  }).on('click', function() {
    that.moveHairlineToTop(h);
  });

  return h;
};

// Moves a hairline's divs to the top of the z-ordering.
hairlines.prototype.moveHairlineToTop = function(h) {
  var div = this.dygraph_.graphDiv;
  $(h.infoDiv).appendTo(div);
  $(h.lineDiv).appendTo(div);

  var idx = this.hairlines_.indexOf(h);
  this.hairlines_.splice(idx, 1);
  this.hairlines_.push(h);
};

// Positions existing hairline divs.
hairlines.prototype.updateHairlineDivPositions = function() {
  var g = this.dygraph_;
  var layout = this.dygraph_.getArea();
  var chartLeft = layout.x, chartRight = layout.x + layout.w;
  var div = this.dygraph_.graphDiv;
  var pos = Dygraph.findPos(div);
  var box = [layout.x + pos.x, layout.y + pos.y];
  box.push(box[0] + layout.w);
  box.push(box[1] + layout.h);

  $.each(this.hairlines_, function(idx, h) {
    var left = g.toDomXCoord(h.xval);
    h.domX = left;  // See comments in this.dataDidUpdate
    $(h.lineDiv).css({
      'left': left + 'px',
      'top': layout.y + 'px',
      'height': layout.h + 'px'
    });  // .draggable("option", "containment", box);
    $(h.infoDiv).css({
      'left': left + 'px',
      'top': layout.y + 'px',
    }).draggable("option", "containment", box);

    var visible = (left >= chartLeft && left <= chartRight);
    $([h.infoDiv, h.lineDiv]).toggle(visible);
  });
};

// Sets styles on the hairline (i.e. "selected")
hairlines.prototype.updateHairlineStyles = function() {
  $.each(this.hairlines_, function(idx, h) {
    $([h.infoDiv, h.lineDiv]).toggleClass('selected', h.selected);
  });
};

// Find prevRow and nextRow such that
// g.getValue(prevRow, 0) <= xval
// g.getValue(nextRow, 0) >= xval
// g.getValue({prev,next}Row, col) != null, NaN or undefined
// and there's no other row such that:
//   g.getValue(prevRow, 0) < g.getValue(row, 0) < g.getValue(nextRow, 0)
//   g.getValue(row, col) != null, NaN or undefined.
// Returns [prevRow, nextRow]. Either can be null (but not both).
hairlines.findPrevNextRows = function(g, xval, col) {
  var prevRow = null, nextRow = null;
  var numRows = g.numRows();
  for (var row = 0; row < numRows; row++) {
    var yval = g.getValue(row, col);
    if (yval === null || yval === undefined || isNaN(yval)) continue;

    var rowXval = g.getValue(row, 0);
    if (rowXval <= xval) prevRow = row;

    if (rowXval >= xval) {
      nextRow = row;
      break;
    }
  }

  return [prevRow, nextRow];
};

// Fills out the info div based on current coordinates.
hairlines.prototype.updateHairlineInfo = function() {
  var mode = 'closest';

  var g = this.dygraph_;
  var xRange = g.xAxisRange();
  var that = this;
  $.each(this.hairlines_, function(idx, h) {
    // To use generateLegendHTML, we synthesize an array of selected points.
    var selPoints = [];
    var labels = g.getLabels();
    var row, prevRow, nextRow;

    if (!h.interpolated) {
      // "closest point" mode.
      // TODO(danvk): make findClosestRow method public
      row = g.findClosestRow(g.toDomXCoord(h.xval));
      for (var i = 1; i < g.numColumns(); i++) {
        selPoints.push({
          canvasx: 1,  // TODO(danvk): real coordinate
          canvasy: 1,  // TODO(danvk): real coordinate
          xval: h.xval,
          yval: g.getValue(row, i),
          name: labels[i]
        });
      }
    } else {
      // "interpolated" mode.
      for (var i = 1; i < g.numColumns(); i++) {
        var prevNextRow = hairlines.findPrevNextRows(g, h.xval, i);
        prevRow = prevNextRow[0], nextRow = prevNextRow[1];

        // For x-values outside the domain, interpolate "between" the extreme
        // point and itself.
        if (prevRow === null) prevRow = nextRow;
        if (nextRow === null) nextRow = prevRow;

        // linear interpolation
        var prevX = g.getValue(prevRow, 0),
            nextX = g.getValue(nextRow, 0),
            prevY = g.getValue(prevRow, i),
            nextY = g.getValue(nextRow, i),
            frac = prevRow == nextRow ? 0 : (h.xval - prevX) / (nextX - prevX),
            yval = frac * nextY + (1 - frac) * prevY;

        selPoints.push({
          canvasx: 1,  // TODO(danvk): real coordinate
          canvasy: 1,  // TODO(danvk): real coordinate
          xval: h.xval,
          yval: yval,
          prevRow: prevRow,
          nextRow: nextRow,
          name: labels[i]
        });
      }
    }

    if (that.divFiller_) {
      that.divFiller_(h.infoDiv, {
        closestRow: row,
        points: selPoints,
        hairline: that.createPublicHairline_(h),
        dygraph: g
      });
    } else {
      var html = Dygraph.Plugins.Legend.generateLegendHTML(g, h.xval, selPoints, 10);
      $('.hairline-legend', h.infoDiv).html(html);
    }
  });
};

// After a resize, the hairline divs can get dettached from the chart.
// This reattaches them.
hairlines.prototype.attachHairlinesToChart_ = function() {
  var div = this.dygraph_.graphDiv;
  $.each(this.hairlines_, function(idx, h) {
    $([h.lineDiv, h.infoDiv]).appendTo(div);
  });
};

// Deletes a hairline and removes it from the chart.
hairlines.prototype.removeHairline = function(h) {
  var idx = this.hairlines_.indexOf(h);
  if (idx >= 0) {
    this.hairlines_.splice(idx, 1);
    $([h.lineDiv, h.infoDiv]).remove();
  } else {
    Dygraph.warn('Tried to remove non-existent hairline.');
  }
};

hairlines.prototype.didDrawChart = function(e) {
  var g = e.dygraph;

  // Early out in the (common) case of zero hairlines.
  if (this.hairlines_.length === 0) return;

  this.updateHairlineDivPositions();
  this.attachHairlinesToChart_();
  this.updateHairlineInfo();
  this.updateHairlineStyles();
};

hairlines.prototype.dataDidUpdate = function(e) {
  // When the data in the chart updates, the hairlines should stay in the same
  // position on the screen. didDrawChart stores a domX parameter for each
  // hairline. We use that to reposition them on data updates.
  var g = this.dygraph_;
  $.each(this.hairlines_, function(idx, h) {
    if (h.hasOwnProperty('domX')) {
      h.xval = g.toDataXCoord(h.domX);
    }
  });
};

hairlines.prototype.click = function(e) {
  if (this.addTimer_) {
    // Another click is in progress; ignore this one.
    return;
  }

  var area = e.dygraph.getArea();
  var xval = this.dygraph_.toDataXCoord(e.canvasx);

  var that = this;
  this.addTimer_ = setTimeout(function() {
    that.addTimer_ = null;
    that.hairlines_.push(that.createHairline({xval: xval}));

    that.updateHairlineDivPositions();
    that.updateHairlineInfo();
    that.updateHairlineStyles();
    that.attachHairlinesToChart_();

    $(that).triggerHandler('hairlineCreated', {
      xval: xval
    });
    $(that).triggerHandler('hairlinesChanged', {});
  }, CLICK_DELAY_MS);
};

hairlines.prototype.dblclick = function(e) {
  if (this.addTimer_) {
    clearTimeout(this.addTimer_);
    this.addTimer_ = null;
  }
};

hairlines.prototype.destroy = function() {
  this.detachLabels();
};


// Public API

/**
 * This is a restricted view of this.hairlines_ which doesn't expose
 * implementation details like the handle divs.
 *
 * @typedef {
 *   xval:  number,       // x-value (i.e. millis or a raw number)
 *   interpolated: bool,  // alternative is to snap to closest
 *   selected: bool       // whether the hairline is selected.
 * } PublicHairline
 */

/**
 * @param {!Hairline} h Internal hairline.
 * @return {!PublicHairline} Restricted public view of the hairline.
 */
hairlines.prototype.createPublicHairline_ = function(h) {
  return {
    xval: h.xval,
    interpolated: h.interpolated,
    selected: h.selected
  };
};

/**
 * @return {!Array.<!PublicHairline>} The current set of hairlines, ordered
 *     from back to front.
 */
hairlines.prototype.get = function() {
  var result = [];
  for (var i = 0; i < this.hairlines_.length; i++) {
    var h = this.hairlines_[i];
    result.push(this.createPublicHairline_(h));
  }
  return result;
};

/**
 * Calling this will result in a hairlinesChanged event being triggered, no
 * matter whether it consists of additions, deletions, moves or no changes at
 * all.
 *
 * @param {!Array.<!PublicHairline>} hairlines The new set of hairlines,
 *     ordered from back to front.
 */
hairlines.prototype.set = function(hairlines) {
  // Re-use divs from the old hairlines array so far as we can.
  // They're already correctly z-ordered.
  var anyCreated = false;
  for (var i = 0; i < hairlines.length; i++) {
    var h = hairlines[i];

    if (this.hairlines_.length > i) {
      this.hairlines_[i].xval = h.xval;
      this.hairlines_[i].interpolated = h.interpolated;
      this.hairlines_[i].selected = h.selected;
    } else {
      this.hairlines_.push(this.createHairline({
        xval: h.xval,
        interpolated: h.interpolated,
        selected: h.selected
      }));
      anyCreated = true;
    }
  }

  // If there are any remaining hairlines, destroy them.
  while (hairlines.length < this.hairlines_.length) {
    this.removeHairline(this.hairlines_[hairlines.length]);
  }

  this.updateHairlineDivPositions();
  this.updateHairlineInfo();
  this.updateHairlineStyles();
  if (anyCreated) {
    this.attachHairlinesToChart_();
  }

  $(this).triggerHandler('hairlinesChanged', {});
};

return hairlines;

})();
