/**
 * @license
 * Copyright 2011 Paul Felix (paul.eric.felix@gmail.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */
/*global Dygraph:false,TouchEvent:false */

/**
 * @fileoverview This file contains the RangeSelector plugin used to provide
 * a timeline range selector widget for dygraphs.
 */

Dygraph.Plugins.RangeSelector = (function() {

/*global Dygraph:false */
"use strict";

var rangeSelector = function() {
  this.isIE_ = /MSIE/.test(navigator.userAgent) && !window.opera;
  this.hasTouchInterface_ = typeof(TouchEvent) != 'undefined';
  this.isMobileDevice_ = /mobile|android/gi.test(navigator.appVersion);
  this.interfaceCreated_ = false;
};

rangeSelector.prototype.toString = function() {
  return "RangeSelector Plugin";
};

rangeSelector.prototype.activate = function(dygraph) {
  this.dygraph_ = dygraph;
  this.isUsingExcanvas_ = dygraph.isUsingExcanvas_;
  if (this.getOption_('showRangeSelector')) {
    this.createInterface_();
  }
  return {
    layout: this.reserveSpace_,
    predraw: this.renderStaticLayer_,
    didDrawChart: this.renderInteractiveLayer_
  };
};

rangeSelector.prototype.destroy = function() {
  this.bgcanvas_ = null;
  this.fgcanvas_ = null;
  this.leftZoomHandle_ = null;
  this.rightZoomHandle_ = null;
  this.iePanOverlay_ = null;
};

//------------------------------------------------------------------
// Private methods
//------------------------------------------------------------------

rangeSelector.prototype.getOption_ = function(name, opt_series) {
  return this.dygraph_.getOption(name, opt_series);
};

rangeSelector.prototype.setDefaultOption_ = function(name, value) {
  this.dygraph_.attrs_[name] = value;
};

/**
 * @private
 * Creates the range selector elements and adds them to the graph.
 */
rangeSelector.prototype.createInterface_ = function() {
  this.createCanvases_();
  if (this.isUsingExcanvas_) {
    this.createIEPanOverlay_();
  }
  this.createZoomHandles_();
  this.initInteraction_();

  // Range selector and animatedZooms have a bad interaction. See issue 359.
  if (this.getOption_('animatedZooms')) {
    console.warn('Animated zooms and range selector are not compatible; disabling animatedZooms.');
    this.dygraph_.updateOptions({animatedZooms: false}, true);
  }

  this.interfaceCreated_ = true;
  this.addToGraph_();
};

/**
 * @private
 * Adds the range selector to the graph.
 */
rangeSelector.prototype.addToGraph_ = function() {
  var graphDiv = this.graphDiv_ = this.dygraph_.graphDiv;
  graphDiv.appendChild(this.bgcanvas_);
  graphDiv.appendChild(this.fgcanvas_);
  graphDiv.appendChild(this.leftZoomHandle_);
  graphDiv.appendChild(this.rightZoomHandle_);
};

/**
 * @private
 * Removes the range selector from the graph.
 */
rangeSelector.prototype.removeFromGraph_ = function() {
  var graphDiv = this.graphDiv_;
  graphDiv.removeChild(this.bgcanvas_);
  graphDiv.removeChild(this.fgcanvas_);
  graphDiv.removeChild(this.leftZoomHandle_);
  graphDiv.removeChild(this.rightZoomHandle_);
  this.graphDiv_ = null;
};

/**
 * @private
 * Called by Layout to allow range selector to reserve its space.
 */
rangeSelector.prototype.reserveSpace_ = function(e) {
  if (this.getOption_('showRangeSelector')) {
    e.reserveSpaceBottom(this.getOption_('rangeSelectorHeight') + 4);
  }
};

/**
 * @private
 * Renders the static portion of the range selector at the predraw stage.
 */
rangeSelector.prototype.renderStaticLayer_ = function() {
  if (!this.updateVisibility_()) {
    return;
  }
  this.resize_();
  this.drawStaticLayer_();
};

/**
 * @private
 * Renders the interactive portion of the range selector after the chart has been drawn.
 */
rangeSelector.prototype.renderInteractiveLayer_ = function() {
  if (!this.updateVisibility_() || this.isChangingRange_) {
    return;
  }
  this.placeZoomHandles_();
  this.drawInteractiveLayer_();
};

/**
 * @private
 * Check to see if the range selector is enabled/disabled and update visibility accordingly.
 */
rangeSelector.prototype.updateVisibility_ = function() {
  var enabled = this.getOption_('showRangeSelector');
  if (enabled) {
    if (!this.interfaceCreated_) {
      this.createInterface_();
    } else if (!this.graphDiv_ || !this.graphDiv_.parentNode) {
      this.addToGraph_();
    }
  } else if (this.graphDiv_) {
    this.removeFromGraph_();
    var dygraph = this.dygraph_;
    setTimeout(function() { dygraph.width_ = 0; dygraph.resize(); }, 1);
  }
  return enabled;
};

/**
 * @private
 * Resizes the range selector.
 */
rangeSelector.prototype.resize_ = function() {
  function setElementRect(canvas, context, rect) {
    var canvasScale = Dygraph.getContextPixelRatio(context);

    canvas.style.top = rect.y + 'px';
    canvas.style.left = rect.x + 'px';
    canvas.width = rect.w * canvasScale;
    canvas.height = rect.h * canvasScale;
    canvas.style.width = rect.w + 'px';
    canvas.style.height = rect.h + 'px';

    if(canvasScale != 1) {
      context.scale(canvasScale, canvasScale);
    }
  }

  var plotArea = this.dygraph_.layout_.getPlotArea();
  
  var xAxisLabelHeight = 0;
  if (this.dygraph_.getOptionForAxis('drawAxis', 'x')) {
    xAxisLabelHeight = this.getOption_('xAxisHeight') || (this.getOption_('axisLabelFontSize') + 2 * this.getOption_('axisTickSize'));
  }
  this.canvasRect_ = {
    x: plotArea.x,
    y: plotArea.y + plotArea.h + xAxisLabelHeight + 4,
    w: plotArea.w,
    h: this.getOption_('rangeSelectorHeight')
  };

  setElementRect(this.bgcanvas_, this.bgcanvas_ctx_, this.canvasRect_);
  setElementRect(this.fgcanvas_, this.fgcanvas_ctx_, this.canvasRect_);
};

/**
 * @private
 * Creates the background and foreground canvases.
 */
rangeSelector.prototype.createCanvases_ = function() {
  this.bgcanvas_ = Dygraph.createCanvas();
  this.bgcanvas_.className = 'dygraph-rangesel-bgcanvas';
  this.bgcanvas_.style.position = 'absolute';
  this.bgcanvas_.style.zIndex = 9;
  this.bgcanvas_ctx_ = Dygraph.getContext(this.bgcanvas_);

  this.fgcanvas_ = Dygraph.createCanvas();
  this.fgcanvas_.className = 'dygraph-rangesel-fgcanvas';
  this.fgcanvas_.style.position = 'absolute';
  this.fgcanvas_.style.zIndex = 9;
  this.fgcanvas_.style.cursor = 'default';
  this.fgcanvas_ctx_ = Dygraph.getContext(this.fgcanvas_);
};

/**
 * @private
 * Creates overlay divs for IE/Excanvas so that mouse events are handled properly.
 */
rangeSelector.prototype.createIEPanOverlay_ = function() {
  this.iePanOverlay_ = document.createElement("div");
  this.iePanOverlay_.style.position = 'absolute';
  this.iePanOverlay_.style.backgroundColor = 'white';
  this.iePanOverlay_.style.filter = 'alpha(opacity=0)';
  this.iePanOverlay_.style.display = 'none';
  this.iePanOverlay_.style.cursor = 'move';
  this.fgcanvas_.appendChild(this.iePanOverlay_);
};

/**
 * @private
 * Creates the zoom handle elements.
 */
rangeSelector.prototype.createZoomHandles_ = function() {
  var img = new Image();
  img.className = 'dygraph-rangesel-zoomhandle';
  img.style.position = 'absolute';
  img.style.zIndex = 10;
  img.style.visibility = 'hidden'; // Initially hidden so they don't show up in the wrong place.
  img.style.cursor = 'col-resize';

  if (/MSIE 7/.test(navigator.userAgent)) { // IE7 doesn't support embedded src data.
    img.width = 7;
    img.height = 14;
    img.style.backgroundColor = 'white';
    img.style.border = '1px solid #333333'; // Just show box in IE7.
  } else {
    img.width = 9;
    img.height = 16;
    img.src = 'data:image/png;base64,' +
'iVBORw0KGgoAAAANSUhEUgAAAAkAAAAQCAYAAADESFVDAAAAAXNSR0IArs4c6QAAAAZiS0dEANAA' +
'zwDP4Z7KegAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB9sHGw0cMqdt1UwAAAAZdEVYdENv' +
'bW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAAAaElEQVQoz+3SsRFAQBCF4Z9WJM8KCDVwownl' +
'6YXsTmCUsyKGkZzcl7zkz3YLkypgAnreFmDEpHkIwVOMfpdi9CEEN2nGpFdwD03yEqDtOgCaun7s' +
'qSTDH32I1pQA2Pb9sZecAxc5r3IAb21d6878xsAAAAAASUVORK5CYII=';
  }

  if (this.isMobileDevice_) {
    img.width *= 2;
    img.height *= 2;
  }

  this.leftZoomHandle_ = img;
  this.rightZoomHandle_ = img.cloneNode(false);
};

/**
 * @private
 * Sets up the interaction for the range selector.
 */
rangeSelector.prototype.initInteraction_ = function() {
  var self = this;
  var topElem = document;
  var clientXLast = 0;
  var handle = null;
  var isZooming = false;
  var isPanning = false;
  var dynamic = !this.isMobileDevice_ && !this.isUsingExcanvas_;

  // We cover iframes during mouse interactions. See comments in
  // dygraph-utils.js for more info on why this is a good idea.
  var tarp = new Dygraph.IFrameTarp();

  // functions, defined below.  Defining them this way (rather than with
  // "function foo() {...}" makes JSHint happy.
  var toXDataWindow, onZoomStart, onZoom, onZoomEnd, doZoom, isMouseInPanZone,
      onPanStart, onPan, onPanEnd, doPan, onCanvasHover;

  // Touch event functions
  var onZoomHandleTouchEvent, onCanvasTouchEvent, addTouchEvents;

  toXDataWindow = function(zoomHandleStatus) {
    var xDataLimits = self.dygraph_.xAxisExtremes();
    var fact = (xDataLimits[1] - xDataLimits[0])/self.canvasRect_.w;
    var xDataMin = xDataLimits[0] + (zoomHandleStatus.leftHandlePos - self.canvasRect_.x)*fact;
    var xDataMax = xDataLimits[0] + (zoomHandleStatus.rightHandlePos - self.canvasRect_.x)*fact;
    return [xDataMin, xDataMax];
  };

  onZoomStart = function(e) {
    Dygraph.cancelEvent(e);
    isZooming = true;
    clientXLast = e.clientX;
    handle = e.target ? e.target : e.srcElement;
    if (e.type === 'mousedown' || e.type === 'dragstart') {
      // These events are removed manually.
      Dygraph.addEvent(topElem, 'mousemove', onZoom);
      Dygraph.addEvent(topElem, 'mouseup', onZoomEnd);
    }
    self.fgcanvas_.style.cursor = 'col-resize';
    tarp.cover();
    return true;
  };

  onZoom = function(e) {
    if (!isZooming) {
      return false;
    }
    Dygraph.cancelEvent(e);

    var delX = e.clientX - clientXLast;
    if (Math.abs(delX) < 4) {
      return true;
    }
    clientXLast = e.clientX;

    // Move handle.
    var zoomHandleStatus = self.getZoomHandleStatus_();
    var newPos;
    if (handle == self.leftZoomHandle_) {
      newPos = zoomHandleStatus.leftHandlePos + delX;
      newPos = Math.min(newPos, zoomHandleStatus.rightHandlePos - handle.width - 3);
      newPos = Math.max(newPos, self.canvasRect_.x);
    } else {
      newPos = zoomHandleStatus.rightHandlePos + delX;
      newPos = Math.min(newPos, self.canvasRect_.x + self.canvasRect_.w);
      newPos = Math.max(newPos, zoomHandleStatus.leftHandlePos + handle.width + 3);
    }
    var halfHandleWidth = handle.width/2;
    handle.style.left = (newPos - halfHandleWidth) + 'px';
    self.drawInteractiveLayer_();

    // Zoom on the fly (if not using excanvas).
    if (dynamic) {
      doZoom();
    }
    return true;
  };

  onZoomEnd = function(e) {
    if (!isZooming) {
      return false;
    }
    isZooming = false;
    tarp.uncover();
    Dygraph.removeEvent(topElem, 'mousemove', onZoom);
    Dygraph.removeEvent(topElem, 'mouseup', onZoomEnd);
    self.fgcanvas_.style.cursor = 'default';

    // If using excanvas, Zoom now.
    if (!dynamic) {
      doZoom();
    }
    return true;
  };

  doZoom = function() {
    try {
      var zoomHandleStatus = self.getZoomHandleStatus_();
      self.isChangingRange_ = true;
      if (!zoomHandleStatus.isZoomed) {
        self.dygraph_.resetZoom();
      } else {
        var xDataWindow = toXDataWindow(zoomHandleStatus);
        self.dygraph_.doZoomXDates_(xDataWindow[0], xDataWindow[1]);
      }
    } finally {
      self.isChangingRange_ = false;
    }
  };

  isMouseInPanZone = function(e) {
    if (self.isUsingExcanvas_) {
        return e.srcElement == self.iePanOverlay_;
    } else {
      var rect = self.leftZoomHandle_.getBoundingClientRect();
      var leftHandleClientX = rect.left + rect.width/2;
      rect = self.rightZoomHandle_.getBoundingClientRect();
      var rightHandleClientX = rect.left + rect.width/2;
      return (e.clientX > leftHandleClientX && e.clientX < rightHandleClientX);
    }
  };

  onPanStart = function(e) {
    if (!isPanning && isMouseInPanZone(e) && self.getZoomHandleStatus_().isZoomed) {
      Dygraph.cancelEvent(e);
      isPanning = true;
      clientXLast = e.clientX;
      if (e.type === 'mousedown') {
        // These events are removed manually.
        Dygraph.addEvent(topElem, 'mousemove', onPan);
        Dygraph.addEvent(topElem, 'mouseup', onPanEnd);
      }
      return true;
    }
    return false;
  };

  onPan = function(e) {
    if (!isPanning) {
      return false;
    }
    Dygraph.cancelEvent(e);

    var delX = e.clientX - clientXLast;
    if (Math.abs(delX) < 4) {
      return true;
    }
    clientXLast = e.clientX;

    // Move range view
    var zoomHandleStatus = self.getZoomHandleStatus_();
    var leftHandlePos = zoomHandleStatus.leftHandlePos;
    var rightHandlePos = zoomHandleStatus.rightHandlePos;
    var rangeSize = rightHandlePos - leftHandlePos;
    if (leftHandlePos + delX <= self.canvasRect_.x) {
      leftHandlePos = self.canvasRect_.x;
      rightHandlePos = leftHandlePos + rangeSize;
    } else if (rightHandlePos + delX >= self.canvasRect_.x + self.canvasRect_.w) {
      rightHandlePos = self.canvasRect_.x + self.canvasRect_.w;
      leftHandlePos = rightHandlePos - rangeSize;
    } else {
      leftHandlePos += delX;
      rightHandlePos += delX;
    }
    var halfHandleWidth = self.leftZoomHandle_.width/2;
    self.leftZoomHandle_.style.left = (leftHandlePos - halfHandleWidth) + 'px';
    self.rightZoomHandle_.style.left = (rightHandlePos - halfHandleWidth) + 'px';
    self.drawInteractiveLayer_();

    // Do pan on the fly (if not using excanvas).
    if (dynamic) {
      doPan();
    }
    return true;
  };

  onPanEnd = function(e) {
    if (!isPanning) {
      return false;
    }
    isPanning = false;
    Dygraph.removeEvent(topElem, 'mousemove', onPan);
    Dygraph.removeEvent(topElem, 'mouseup', onPanEnd);
    // If using excanvas, do pan now.
    if (!dynamic) {
      doPan();
    }
    return true;
  };

  doPan = function() {
    try {
      self.isChangingRange_ = true;
      self.dygraph_.dateWindow_ = toXDataWindow(self.getZoomHandleStatus_());
      self.dygraph_.drawGraph_(false);
    } finally {
      self.isChangingRange_ = false;
    }
  };

  onCanvasHover = function(e) {
    if (isZooming || isPanning) {
      return;
    }
    var cursor = isMouseInPanZone(e) ? 'move' : 'default';
    if (cursor != self.fgcanvas_.style.cursor) {
      self.fgcanvas_.style.cursor = cursor;
    }
  };

  onZoomHandleTouchEvent = function(e) {
    if (e.type == 'touchstart' && e.targetTouches.length == 1) {
      if (onZoomStart(e.targetTouches[0])) {
        Dygraph.cancelEvent(e);
      }
    } else if (e.type == 'touchmove' && e.targetTouches.length == 1) {
      if (onZoom(e.targetTouches[0])) {
        Dygraph.cancelEvent(e);
      }
    } else {
      onZoomEnd(e);
    }
  };

  onCanvasTouchEvent = function(e) {
    if (e.type == 'touchstart' && e.targetTouches.length == 1) {
      if (onPanStart(e.targetTouches[0])) {
        Dygraph.cancelEvent(e);
      }
    } else if (e.type == 'touchmove' && e.targetTouches.length == 1) {
      if (onPan(e.targetTouches[0])) {
        Dygraph.cancelEvent(e);
      }
    } else {
      onPanEnd(e);
    }
  };

  addTouchEvents = function(elem, fn) {
    var types = ['touchstart', 'touchend', 'touchmove', 'touchcancel'];
    for (var i = 0; i < types.length; i++) {
      self.dygraph_.addAndTrackEvent(elem, types[i], fn);
    }
  };

  this.setDefaultOption_('interactionModel', Dygraph.Interaction.dragIsPanInteractionModel);
  this.setDefaultOption_('panEdgeFraction', 0.0001);

  var dragStartEvent = window.opera ? 'mousedown' : 'dragstart';
  this.dygraph_.addAndTrackEvent(this.leftZoomHandle_, dragStartEvent, onZoomStart);
  this.dygraph_.addAndTrackEvent(this.rightZoomHandle_, dragStartEvent, onZoomStart);

  if (this.isUsingExcanvas_) {
    this.dygraph_.addAndTrackEvent(this.iePanOverlay_, 'mousedown', onPanStart);
  } else {
    this.dygraph_.addAndTrackEvent(this.fgcanvas_, 'mousedown', onPanStart);
    this.dygraph_.addAndTrackEvent(this.fgcanvas_, 'mousemove', onCanvasHover);
  }

  // Touch events
  if (this.hasTouchInterface_) {
    addTouchEvents(this.leftZoomHandle_, onZoomHandleTouchEvent);
    addTouchEvents(this.rightZoomHandle_, onZoomHandleTouchEvent);
    addTouchEvents(this.fgcanvas_, onCanvasTouchEvent);
  }
};

/**
 * @private
 * Draws the static layer in the background canvas.
 */
rangeSelector.prototype.drawStaticLayer_ = function() {
  var ctx = this.bgcanvas_ctx_;
  ctx.clearRect(0, 0, this.canvasRect_.w, this.canvasRect_.h);
  try {
    this.drawMiniPlot_();
  } catch(ex) {
    console.warn(ex);
  }

  var margin = 0.5;
  this.bgcanvas_ctx_.lineWidth = 1;
  ctx.strokeStyle = 'gray';
  ctx.beginPath();
  ctx.moveTo(margin, margin);
  ctx.lineTo(margin, this.canvasRect_.h-margin);
  ctx.lineTo(this.canvasRect_.w-margin, this.canvasRect_.h-margin);
  ctx.lineTo(this.canvasRect_.w-margin, margin);
  ctx.stroke();
};


/**
 * @private
 * Draws the mini plot in the background canvas.
 */
rangeSelector.prototype.drawMiniPlot_ = function() {
  var fillStyle = this.getOption_('rangeSelectorPlotFillColor');
  var strokeStyle = this.getOption_('rangeSelectorPlotStrokeColor');
  if (!fillStyle && !strokeStyle) {
    return;
  }

  var stepPlot = this.getOption_('stepPlot');

  var combinedSeriesData = this.computeCombinedSeriesAndLimits_();
  var yRange = combinedSeriesData.yMax - combinedSeriesData.yMin;

  // Draw the mini plot.
  var ctx = this.bgcanvas_ctx_;
  var margin = 0.5;

  var xExtremes = this.dygraph_.xAxisExtremes();
  var xRange = Math.max(xExtremes[1] - xExtremes[0], 1.e-30);
  var xFact = (this.canvasRect_.w - margin)/xRange;
  var yFact = (this.canvasRect_.h - margin)/yRange;
  var canvasWidth = this.canvasRect_.w - margin;
  var canvasHeight = this.canvasRect_.h - margin;

  var prevX = null, prevY = null;

  ctx.beginPath();
  ctx.moveTo(margin, canvasHeight);
  for (var i = 0; i < combinedSeriesData.data.length; i++) {
    var dataPoint = combinedSeriesData.data[i];
    var x = ((dataPoint[0] !== null) ? ((dataPoint[0] - xExtremes[0])*xFact) : NaN);
    var y = ((dataPoint[1] !== null) ? (canvasHeight - (dataPoint[1] - combinedSeriesData.yMin)*yFact) : NaN);

    // Skip points that don't change the x-value. Overly fine-grained points
    // can cause major slowdowns with the ctx.fill() call below.
    if (!stepPlot && prevX !== null && Math.round(x) == Math.round(prevX)) {
      continue;
    }

    if (isFinite(x) && isFinite(y)) {
      if(prevX === null) {
        ctx.lineTo(x, canvasHeight);
      }
      else if (stepPlot) {
        ctx.lineTo(x, prevY);
      }
      ctx.lineTo(x, y);
      prevX = x;
      prevY = y;
    }
    else {
      if(prevX !== null) {
        if (stepPlot) {
          ctx.lineTo(x, prevY);
          ctx.lineTo(x, canvasHeight);
        }
        else {
          ctx.lineTo(prevX, canvasHeight);
        }
      }
      prevX = prevY = null;
    }
  }
  ctx.lineTo(canvasWidth, canvasHeight);
  ctx.closePath();

  if (fillStyle) {
    var lingrad = this.bgcanvas_ctx_.createLinearGradient(0, 0, 0, canvasHeight);
    lingrad.addColorStop(0, 'white');
    lingrad.addColorStop(1, fillStyle);
    this.bgcanvas_ctx_.fillStyle = lingrad;
    ctx.fill();
  }

  if (strokeStyle) {
    this.bgcanvas_ctx_.strokeStyle = strokeStyle;
    this.bgcanvas_ctx_.lineWidth = 1.5;
    ctx.stroke();
  }
};

/**
 * @private
 * Computes and returns the combined series data along with min/max for the mini plot.
 * The combined series consists of averaged values for all series.
 * When series have error bars, the error bars are ignored.
 * @return {Object} An object containing combined series array, ymin, ymax.
 */
rangeSelector.prototype.computeCombinedSeriesAndLimits_ = function() {
  var g = this.dygraph_;
  var logscale = this.getOption_('logscale');
  var i;

  // Select series to combine. By default, all series are combined.
  var numColumns = g.numColumns();
  var labels = g.getLabels();
  var includeSeries = new Array(numColumns);
  var anySet = false;
  for (i = 1; i < numColumns; i++) {
    var include = this.getOption_('showInRangeSelector', labels[i]);
    includeSeries[i] = include;
    if (include !== null) anySet = true;  // it's set explicitly for this series
  }
  if (!anySet) {
    for (i = 0; i < includeSeries.length; i++) includeSeries[i] = true;
  }

  // Create a combined series (average of selected series values).
  // TODO(danvk): short-circuit if there's only one series.
  var rolledSeries = [];
  var dataHandler = g.dataHandler_;
  var options = g.attributes_;
  for (i = 1; i < g.numColumns(); i++) {
    if (!includeSeries[i]) continue;
    var series = dataHandler.extractSeries(g.rawData_, i, options);
    if (g.rollPeriod() > 1) {
      series = dataHandler.rollingAverage(series, g.rollPeriod(), options);
    }
    
    rolledSeries.push(series);
  }

  var combinedSeries = [];
  for (i = 0; i < rolledSeries[0].length; i++) {
    var sum = 0;
    var count = 0;
    for (var j = 0; j < rolledSeries.length; j++) {
      var y = rolledSeries[j][i][1];
      if (y === null || isNaN(y)) continue;
      count++;
      sum += y;
    }
    combinedSeries.push([rolledSeries[0][i][0], sum / count]);
  }

  // Compute the y range.
  var yMin = Number.MAX_VALUE;
  var yMax = -Number.MAX_VALUE;
  for (i = 0; i < combinedSeries.length; i++) {
    var yVal = combinedSeries[i][1];
    if (yVal !== null && isFinite(yVal) && (!logscale || yVal > 0)) {
      yMin = Math.min(yMin, yVal);
      yMax = Math.max(yMax, yVal);
    }
  }

  // Convert Y data to log scale if needed.
  // Also, expand the Y range to compress the mini plot a little.
  var extraPercent = 0.25;
  if (logscale) {
    yMax = Dygraph.log10(yMax);
    yMax += yMax*extraPercent;
    yMin = Dygraph.log10(yMin);
    for (i = 0; i < combinedSeries.length; i++) {
      combinedSeries[i][1] = Dygraph.log10(combinedSeries[i][1]);
    }
  } else {
    var yExtra;
    var yRange = yMax - yMin;
    if (yRange <= Number.MIN_VALUE) {
      yExtra = yMax*extraPercent;
    } else {
      yExtra = yRange*extraPercent;
    }
    yMax += yExtra;
    yMin -= yExtra;
  }

  return {data: combinedSeries, yMin: yMin, yMax: yMax};
};

/**
 * @private
 * Places the zoom handles in the proper position based on the current X data window.
 */
rangeSelector.prototype.placeZoomHandles_ = function() {
  var xExtremes = this.dygraph_.xAxisExtremes();
  var xWindowLimits = this.dygraph_.xAxisRange();
  var xRange = xExtremes[1] - xExtremes[0];
  var leftPercent = Math.max(0, (xWindowLimits[0] - xExtremes[0])/xRange);
  var rightPercent = Math.max(0, (xExtremes[1] - xWindowLimits[1])/xRange);
  var leftCoord = this.canvasRect_.x + this.canvasRect_.w*leftPercent;
  var rightCoord = this.canvasRect_.x + this.canvasRect_.w*(1 - rightPercent);
  var handleTop = Math.max(this.canvasRect_.y, this.canvasRect_.y + (this.canvasRect_.h - this.leftZoomHandle_.height)/2);
  var halfHandleWidth = this.leftZoomHandle_.width/2;
  this.leftZoomHandle_.style.left = (leftCoord - halfHandleWidth) + 'px';
  this.leftZoomHandle_.style.top = handleTop + 'px';
  this.rightZoomHandle_.style.left = (rightCoord - halfHandleWidth) + 'px';
  this.rightZoomHandle_.style.top = this.leftZoomHandle_.style.top;

  this.leftZoomHandle_.style.visibility = 'visible';
  this.rightZoomHandle_.style.visibility = 'visible';
};

/**
 * @private
 * Draws the interactive layer in the foreground canvas.
 */
rangeSelector.prototype.drawInteractiveLayer_ = function() {
  var ctx = this.fgcanvas_ctx_;
  ctx.clearRect(0, 0, this.canvasRect_.w, this.canvasRect_.h);
  var margin = 1;
  var width = this.canvasRect_.w - margin;
  var height = this.canvasRect_.h - margin;
  var zoomHandleStatus = this.getZoomHandleStatus_();

  ctx.strokeStyle = 'black';
  if (!zoomHandleStatus.isZoomed) {
    ctx.beginPath();
    ctx.moveTo(margin, margin);
    ctx.lineTo(margin, height);
    ctx.lineTo(width, height);
    ctx.lineTo(width, margin);
    ctx.stroke();
    if (this.iePanOverlay_) {
      this.iePanOverlay_.style.display = 'none';
    }
  } else {
    var leftHandleCanvasPos = Math.max(margin, zoomHandleStatus.leftHandlePos - this.canvasRect_.x);
    var rightHandleCanvasPos = Math.min(width, zoomHandleStatus.rightHandlePos - this.canvasRect_.x);

    ctx.fillStyle = 'rgba(240, 240, 240, 0.6)';
    ctx.fillRect(0, 0, leftHandleCanvasPos, this.canvasRect_.h);
    ctx.fillRect(rightHandleCanvasPos, 0, this.canvasRect_.w - rightHandleCanvasPos, this.canvasRect_.h);

    ctx.beginPath();
    ctx.moveTo(margin, margin);
    ctx.lineTo(leftHandleCanvasPos, margin);
    ctx.lineTo(leftHandleCanvasPos, height);
    ctx.lineTo(rightHandleCanvasPos, height);
    ctx.lineTo(rightHandleCanvasPos, margin);
    ctx.lineTo(width, margin);
    ctx.stroke();

    if (this.isUsingExcanvas_) {
      this.iePanOverlay_.style.width = (rightHandleCanvasPos - leftHandleCanvasPos) + 'px';
      this.iePanOverlay_.style.left = leftHandleCanvasPos + 'px';
      this.iePanOverlay_.style.height = height + 'px';
      this.iePanOverlay_.style.display = 'inline';
    }
  }
};

/**
 * @private
 * Returns the current zoom handle position information.
 * @return {Object} The zoom handle status.
 */
rangeSelector.prototype.getZoomHandleStatus_ = function() {
  var halfHandleWidth = this.leftZoomHandle_.width/2;
  var leftHandlePos = parseFloat(this.leftZoomHandle_.style.left) + halfHandleWidth;
  var rightHandlePos = parseFloat(this.rightZoomHandle_.style.left) + halfHandleWidth;
  return {
      leftHandlePos: leftHandlePos,
      rightHandlePos: rightHandlePos,
      isZoomed: (leftHandlePos - 1 > this.canvasRect_.x || rightHandlePos + 1 < this.canvasRect_.x+this.canvasRect_.w)
  };
};

return rangeSelector;

})();
