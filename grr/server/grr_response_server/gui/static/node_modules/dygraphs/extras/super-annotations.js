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

Dygraph.Plugins.SuperAnnotations = (function() {

"use strict";

/**
 * These are just the basic requirements -- annotations can have whatever other
 * properties the code that displays them wants them to have.
 *
 * @typedef {
 *   xval:  number,      // x-value (i.e. millis or a raw number)
 *   series: string,     // series name
 *   yFrac: ?number,     // y-positioning. Default is a few px above the point.
 *   lineDiv: !Element   // vertical div connecting point to info div.
 *   infoDiv: !Element   // div containing info about the annotation.
 * } Annotation
 */

var annotations = function(opt_options) {
  /* @type {!Array.<!Annotation>} */
  this.annotations_ = [];
  // Used to detect resizes (which require the divs to be repositioned).
  this.lastWidth_ = -1;
  this.lastHeight = -1;
  this.dygraph_ = null;

  opt_options = opt_options || {};
  this.defaultAnnotationProperties_ = $.extend({
    'text': 'Description'
  }, opt_options['defaultAnnotationProperties']);
};

annotations.prototype.toString = function() {
  return "SuperAnnotations Plugin";
};

annotations.prototype.activate = function(g) {
  this.dygraph_ = g;
  this.annotations_ = [];

  return {
    didDrawChart: this.didDrawChart,
    pointClick: this.pointClick  // TODO(danvk): implement in dygraphs
  };
};

annotations.prototype.detachLabels = function() {
  for (var i = 0; i < this.annotations_.length; i++) {
    var a = this.annotations_[i];
    $(a.lineDiv).remove();
    $(a.infoDiv).remove();
    this.annotations_[i] = null;
  }
  this.annotations_ = [];
};

annotations.prototype.annotationWasDragged = function(a, event, ui) {
  var g = this.dygraph_;
  var area = g.getArea();
  var oldYFrac = a.yFrac;

  var infoDiv = a.infoDiv;
  var newYFrac = ((infoDiv.offsetTop + infoDiv.offsetHeight) - area.y) / area.h;
  if (newYFrac == oldYFrac) return;

  a.yFrac = newYFrac;

  this.moveAnnotationToTop(a);
  this.updateAnnotationDivPositions();
  this.updateAnnotationInfo();
  $(this).triggerHandler('annotationMoved', {
    annotation: a,
    oldYFrac: oldYFrac,
    newYFrac: a.yFrac
  });
  $(this).triggerHandler('annotationsChanged', {});
};

annotations.prototype.makeAnnotationEditable = function(a) {
  if (a.editable == true) return;
  this.moveAnnotationToTop(a);

  // Note: we have to fill out the HTML ourselves because
  // updateAnnotationInfo() won't touch editable annotations.
  a.editable = true;
  var editableTemplateDiv = $('#annotation-editable-template').get(0);
  a.infoDiv.innerHTML = this.getTemplateHTML(editableTemplateDiv, a);
  $(a.infoDiv).toggleClass('editable', !!a.editable);
  $(this).triggerHandler('beganEditAnnotation', a);
};

// This creates the hairline object and returns it.
// It does not position it and does not attach it to the chart.
annotations.prototype.createAnnotation = function(a) {
  var self = this;

  var color = this.getColorForSeries_(a.series);

  var $lineDiv = $('<div/>').css({
    'width': '1px',
    'left': '3px',
    'background': 'black',
    'height': '100%',
    'position': 'absolute',
    // TODO(danvk): use border-color here for consistency?
    'background-color': color,
    'z-index': 10
  }).addClass('dygraph-annotation-line');

  var $infoDiv = $('#annotation-template').clone().removeAttr('id').css({
      'position': 'absolute',
      'border-color': color,
      'z-index': 10
    })
    .show();

  $.extend(a, {
    lineDiv: $lineDiv.get(0),
    infoDiv: $infoDiv.get(0)
  });

  var that = this;

  $infoDiv.draggable({
    'start': function(event, ui) {
      $(this).css({'bottom': ''});
      a.isDragging = true;
    },
    'drag': function(event, ui) {
      self.annotationWasDragged(a, event, ui);
    },
    'stop': function(event, ui) {
      $(this).css({'top': ''});
      a.isDragging = false;
      self.updateAnnotationDivPositions();
    },
    'axis': 'y',
    'containment': 'parent'
  });

  // TODO(danvk): use 'on' instead of delegate/dblclick
  $infoDiv.on('click', '.annotation-kill-button', function() {
    that.removeAnnotation(a);
    $(that).triggerHandler('annotationDeleted', a);
    $(that).triggerHandler('annotationsChanged', {});
  });

  $infoDiv.on('dblclick', function() {
    that.makeAnnotationEditable(a);
  });
  $infoDiv.on('click', '.annotation-update', function() {
    self.extractUpdatedProperties_($infoDiv.get(0), a);
    a.editable = false;
    self.updateAnnotationInfo();
    $(that).triggerHandler('annotationEdited', a);
    $(that).triggerHandler('annotationsChanged', {});
  });
  $infoDiv.on('click', '.annotation-cancel', function() {
    a.editable = false;
    self.updateAnnotationInfo();
    $(that).triggerHandler('cancelEditAnnotation', a);
  });

  return a;
};

// Find the index of a point in a series.
// Returns a 2-element array, [row, col], which can be used with
// dygraph.getValue() to get the value at this point.
// Returns null if there's no match.
annotations.prototype.findPointIndex_ = function(series, xval) {
  var col = this.dygraph_.getLabels().indexOf(series);
  if (col == -1) return null;

  var lowIdx = 0, highIdx = this.dygraph_.numRows() - 1;
  while (lowIdx <= highIdx) {
    var idx = Math.floor((lowIdx + highIdx) / 2);
    var xAtIdx = this.dygraph_.getValue(idx, 0);
    if (xAtIdx == xval) {
      return [idx, col];
    } else if (xAtIdx < xval) {
      lowIdx = idx + 1;
    } else {
      highIdx = idx - 1;
    }
  }
  return null;
};

annotations.prototype.getColorForSeries_ = function(series) {
  var colors = this.dygraph_.getColors();
  var col = this.dygraph_.getLabels().indexOf(series);
  if (col == -1) return null;

  return colors[(col - 1) % colors.length];
};

// Moves a hairline's divs to the top of the z-ordering.
annotations.prototype.moveAnnotationToTop = function(a) {
  var div = this.dygraph_.graphDiv;
  $(a.infoDiv).appendTo(div);
  $(a.lineDiv).appendTo(div);

  var idx = this.annotations_.indexOf(a);
  this.annotations_.splice(idx, 1);
  this.annotations_.push(a);
};

// Positions existing hairline divs.
annotations.prototype.updateAnnotationDivPositions = function() {
  var layout = this.dygraph_.getArea();
  var chartLeft = layout.x, chartRight = layout.x + layout.w;
  var chartTop = layout.y, chartBottom = layout.y + layout.h;
  var div = this.dygraph_.graphDiv;
  var pos = Dygraph.findPos(div);
  var box = [layout.x + pos.x, layout.y + pos.y];
  box.push(box[0] + layout.w);
  box.push(box[1] + layout.h);

  var g = this.dygraph_;

  var that = this;
  $.each(this.annotations_, function(idx, a) {
    var row_col = that.findPointIndex_(a.series, a.xval);
    if (row_col == null) {
      $([a.lineDiv, a.infoDiv]).hide();
      return;
    } else {
      // TODO(danvk): only do this if they're invisible?
      $([a.lineDiv, a.infoDiv]).show();
    }
    var xy = g.toDomCoords(a.xval, g.getValue(row_col[0], row_col[1]));
    var x = xy[0], pointY = xy[1];

    var lineHeight = 6;  // TODO(danvk): option?

    var y = pointY;
    if (a.yFrac !== undefined) {
      y = layout.y + layout.h * a.yFrac;
    } else {
      y -= lineHeight;
    }

    var lineHeight = y < pointY ? (pointY - y) : (y - pointY - a.infoDiv.offsetHeight);
    $(a.lineDiv).css({
      'left': x + 'px',
      'top': Math.min(y, pointY) + 'px',
      'height': lineHeight + 'px'
    });
    $(a.infoDiv).css({
      'left': x + 'px',
    });
    if (!a.isDragging) {
      // jQuery UI draggable likes to set 'top', whereas superannotations sets
      // 'bottom'. Setting both will make the annotation grow and contract as
      // the user drags it, which looks bad.
      $(a.infoDiv).css({
        'bottom': (div.offsetHeight - y) + 'px'
      })  //.draggable("option", "containment", box);

      var visible = (x >= chartLeft && x <= chartRight) &&
                    (pointY >= chartTop && pointY <= chartBottom);
      $([a.infoDiv, a.lineDiv]).toggle(visible);
    }
  });
};

// Fills out the info div based on current coordinates.
annotations.prototype.updateAnnotationInfo = function() {
  var g = this.dygraph_;

  var that = this;
  var templateDiv = $('#annotation-template').get(0);
  $.each(this.annotations_, function(idx, a) {
    // We should never update an editable div -- doing so may kill unsaved
    // edits to an annotation.
    $(a.infoDiv).toggleClass('editable', !!a.editable);
    if (a.editable) return;
    a.infoDiv.innerHTML = that.getTemplateHTML(templateDiv, a);
  });
};

/**
 * @param {!Annotation} a Internal annotation
 * @return {!PublicAnnotation} a view of the annotation for the public API.
 */
annotations.prototype.createPublicAnnotation_ = function(a, opt_props) {
  var displayAnnotation = $.extend({}, a, opt_props);
  delete displayAnnotation['infoDiv'];
  delete displayAnnotation['lineDiv'];
  delete displayAnnotation['isDragging'];
  delete displayAnnotation['editable'];
  return displayAnnotation;
};

// Fill out a div using the values in the annotation object.
// The div's html is expected to have text of the form "{{key}}"
annotations.prototype.getTemplateHTML = function(div, a) {
  var g = this.dygraph_;
  var row_col = this.findPointIndex_(a.series, a.xval);
  if (row_col == null) return;  // perhaps it's no longer a real point?
  var row = row_col[0];
  var col = row_col[1];

  var yOptView = g.optionsViewForAxis_('y1');  // TODO: support secondary, too
  var xvf = g.getOptionForAxis('valueFormatter', 'x');

  var x = xvf.call(g, a.xval);
  var y = g.getOption('valueFormatter', a.series).call(
      g, g.getValue(row, col), yOptView);

  var displayAnnotation = this.createPublicAnnotation_(a, {x:x, y:y});
  var html = div.innerHTML;
  for (var k in displayAnnotation) {
    var v = displayAnnotation[k];
    if (typeof(v) == 'object') continue;  // e.g. infoDiv or lineDiv
    html = html.replace(new RegExp('\{\{' + k + '\}\}', 'g'), v);
  }
  return html;
};

// Update the annotation object by looking for elements with a 'dg-ann-field'
// attribute. For example, <input type='text' dg-ann-field='text' /> will have
// its value placed in the 'text' attribute of the annotation.
annotations.prototype.extractUpdatedProperties_ = function(div, a) {
  $(div).find('[dg-ann-field]').each(function(idx, el) {
    var k = $(el).attr('dg-ann-field');
    var v = $(el).val();
    a[k] = v;
  });
};

// After a resize, the hairline divs can get dettached from the chart.
// This reattaches them.
annotations.prototype.attachAnnotationsToChart_ = function() {
  var div = this.dygraph_.graphDiv;
  $.each(this.annotations_, function(idx, a) {
    // Re-attaching an editable div to the DOM can clear its focus.
    // This makes typing really difficult!
    if (a.editable) return;

    $([a.lineDiv, a.infoDiv]).appendTo(div);
  });
};

// Deletes a hairline and removes it from the chart.
annotations.prototype.removeAnnotation = function(a) {
  var idx = this.annotations_.indexOf(a);
  if (idx >= 0) {
    this.annotations_.splice(idx, 1);
    $([a.lineDiv, a.infoDiv]).remove();
  } else {
    Dygraph.warn('Tried to remove non-existent annotation.');
  }
};

annotations.prototype.didDrawChart = function(e) {
  var g = e.dygraph;

  // Early out in the (common) case of zero annotations.
  if (this.annotations_.length === 0) return;

  this.updateAnnotationDivPositions();
  this.attachAnnotationsToChart_();
  this.updateAnnotationInfo();
};

annotations.prototype.pointClick = function(e) {
  // Prevent any other behavior based on this click, e.g. creation of a hairline.
  e.preventDefault();

  var a = $.extend({}, this.defaultAnnotationProperties_, {
    series: e.point.name,
    xval: e.point.xval
  });
  this.annotations_.push(this.createAnnotation(a));

  this.updateAnnotationDivPositions();
  this.updateAnnotationInfo();
  this.attachAnnotationsToChart_();

  $(this).triggerHandler('annotationCreated', a);
  $(this).triggerHandler('annotationsChanged', {});

  // Annotations should begin life editable.
  this.makeAnnotationEditable(a);
};

annotations.prototype.destroy = function() {
  this.detachLabels();
};


// Public API

/**
 * This is a restricted view of this.annotations_ which doesn't expose
 * implementation details like the line / info divs.
 *
 * @typedef {
 *   xval:  number,      // x-value (i.e. millis or a raw number)
 *   series: string,     // series name
 * } PublicAnnotation
 */

/**
 * @return {!Array.<!PublicAnnotation>} The current set of annotations, ordered
 *     from back to front.
 */
annotations.prototype.get = function() {
  var result = [];
  for (var i = 0; i < this.annotations_.length; i++) {
    result.push(this.createPublicAnnotation_(this.annotations_[i]));
  }
  return result;
};

/**
 * Calling this will result in an annotationsChanged event being triggered, no
 * matter whether it consists of additions, deletions, moves or no changes at
 * all.
 *
 * @param {!Array.<!PublicAnnotation>} annotations The new set of annotations,
 *     ordered from back to front.
 */
annotations.prototype.set = function(annotations) {
  // Re-use divs from the old annotations array so far as we can.
  // They're already correctly z-ordered.
  var anyCreated = false;
  for (var i = 0; i < annotations.length; i++) {
    var a = annotations[i];

    if (this.annotations_.length > i) {
      // Only the divs need to be preserved.
      var oldA = this.annotations_[i];
      this.annotations_[i] = $.extend({
        infoDiv: oldA.infoDiv,
        lineDiv: oldA.lineDiv
      }, a);
    } else {
      this.annotations_.push(this.createAnnotation(a));
      anyCreated = true;
    }
  }

  // If there are any remaining annotations, destroy them.
  while (annotations.length < this.annotations_.length) {
    this.removeAnnotation(this.annotations_[annotations.length]);
  }

  this.updateAnnotationDivPositions();
  this.updateAnnotationInfo();
  if (anyCreated) {
    this.attachAnnotationsToChart_();
  }

  $(this).triggerHandler('annotationsChanged', {});
};

return annotations;

})();
