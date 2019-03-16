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
 * @fileoverview List of options and their types, used for the palette.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */

"use strict";

/**
 * Options availabile to the palette.
 *
 * Each entry is the name of the option, followed by:
 * type: describes the type of option, which can be:
 *   boolean|string|float|int|array<boolean>|array<int>|array<float>|array<Date>
 *   or function(parameter list)
 * scope: if empty, then available in global scope only. Otherwise,
 * it's an array with possible values global|series|x|y|y2|highlight.
 */
var opts = {
  // These two exist, but are not used by the palette at all.
  series : { type : null, scope : [] },
  axes : { type : null, scope : [] },

  animatedZooms : {
    type : "boolean"
  },
  annotationClickHandler : {
    type : "function(annotation, point, dygraph, event)"
  },
  annotationDblClickHandler : {
    type : "function(annotation, point, dygraph, event)"
  },
  annotationMouseOutHandler : {
    type : "function(annotation, point, dygraph, event)"
  },
  annotationMouseOverHandler : {
    type : "function(annotation, point, dygraph, event)"
  },
  avoidMinZero : {
    type : "boolean"
  },
  axis : {
    type : "string",
    scope : [ "series" ]
  },
  axisLabelColor : {
    type : "string",
    scope : [ "global", "x", "y", "y2" ]
  },
  axisLabelFontSize : {
    type : "int",
    scope : [ "global", "x", "y", "y2" ]
  },
  axisLabelFormatter : {
    type : "function(numberOrDate, granularity, opts, dygraph)",
    scope : [ "x", "y", "y2" ]
  },
  axisLabelWidth : {
    type : "int",
    // scope : [ "global", "x", "y", "y2" ]
  },
  axisLineColor : {
    type : "string",
    scope : [ "global", "x", "y", "y2" ]
  },
  axisLineWidth : {
    type : "int",
    scope : [ "global", "x", "y", "y2" ]
  },
  axisTickSize : {
    type : "int",
    // scope : [ "global", "x", "y", "y2" ]
  },
  clickCallback : {
    type : "function(e, x, points)"
  },
  colorSaturation : {
    type : "float"
  },
  colors : {
    type : "array<string>"
  },
  colorValue : {
    type : "float"
  },
  connectSeparatedPoints : {
    type : "boolean"
  },
  customBars : {
    type : "boolean"
  },
  dateWindow : {
    type : "array<Date>"
  },
  delimiter : {
    type : "string"
  },
  digitsAfterDecimal : {
    type : "int"
  },
  displayAnnotations : {
    type : "boolean"
  },
  drawAxesAtZero : {
    type : "boolean"
  },
  drawCallback : {
    type : "function(dygraph, is_initial)"
  },
  drawGapEdgePoints : {
    type : "boolean"
  },
  drawHighlightPointCallback : {
    type : "function(g, seriesName, canvasContext, cx, cy, color, pointSize)",
    scope : [ "global", "series", "y", "y2" ]
  },
  drawPoints : {
    type : "boolean",
    scope : [ "global", "series", "y", "y2" ]
  },
  drawPointCallback : {
    type : "function(g, seriesName, canvasContext, cx, cy, color, pointSize)",
    scope : [ "global", "series", "y", "y2" ]
  },
  drawXAxis : {
    type : "boolean"
  },
  drawXGrid : {
    type : "boolean"
  },
  drawYAxis : {
    type : "boolean"
  },
  drawYGrid : {
    type : "boolean"
  },
  errorBars : {
    type : "boolean"
  },
  fillAlpha : {
    type : "float"
  },
  fillGraph : {
    type : "boolean"
  },
  fractions : {
    type : "boolean"
  },
  gridLineColor : {
    type : "string"
  },
  gridLineWidth : {
    type : "int"
  },
  height : {
    type : "int"
  },
  hideOverlayOnMouseOut : {
    type : "boolean"
  },
  highlightCallback : {
    type : "function(event, x, points,row)"
  },
  highlightCircleSize : {
    type : "int",
    scope : [ "global", "series", "y", "y2" ]
  },
  includeZero : {
    type : "boolean"
  },
  isZoomedIgnoreProgrammaticZoom : {
    type : "boolean"
  },
  labelsDivWidth : {
    type : "integer"
  },
  labels : {
    type : "array<string>"
  },
  labelsKMB : {
    type : "boolean"
  },
  labelsKMG2 : {
    type : "boolean"
  },
  labelsSeparateLines : {
    type : "boolean"
  },
  labelsShowZeroValues : {
    type : "boolean"
  },
  legend : {
    type : "string"
  },
  logscale : {
    type : "boolean"
  },
  maxNumberWidth : {
    type : "int"
  },
  panEdgeFraction : {
    type : "float"
  },
  pixelsPerLabel : {
    type : "int"
  },
  pixelsPerXLabel : {
    type : "int"
  },
  pixelsPerYLabel : {
    type : "int"
  },
  pointClickCallback : {
    type : "function(e, point)"
  },
  pointSize : {
    type : "integer",
    scope : [ "global", "series", "y", "y2" ]
  },
  rangeSelectorHeight : {
    type : "int"
  },
  rangeSelectorPlotFillColor : {
    type : "int"
  },
  rangeSelectorPlotStrokeColor : {
    type : "int"
  },
  rightGap : {
    type : "boolean"
  },
  rollPeriod : {
    type : "int"
  },
  showLabelsOnHighlight : {
    type : "boolean"
  },
  showRangeSelector : {
    type : "boolean"
  },
  showRoller : {
    type : "boolean"
  },
  sigFigs : {
    type : "int"
  },
  sigma : {
    type : "float"
  },
  stackedGraph : {
    type : "boolean"
  },
  stepPlot : {
    type : "boolean"
  },
  strokeBorderColor : {
    type : "string",
    scope : [ "global", "series", "y", "y2" ]
  },
  strokeBorderWidth : {
    type : "float",
    scope : [ "global", "series", "y", "y2" ]
  },
  strokePattern : {
    type : "array<int>",
    scope : [ "global", "series", "y", "y2" ]
  },
  strokeWidth : {
    type : "float",
    scope : [ "global", "series", "y", "y2" ]
  },
  timingName : {
    type : "string"
  },
  title : {
    type : "string"
  },
  titleHeight : {
    type : "integer"
  },
  underlayCallback : {
    type : "function(canvas, area, dygraph)"
  },
  unhighlightCallback : {
    type : "function(event)"
  },
  valueRange : {
    type : "array<float>"
  },
  visibility : {
    type : "array<boolean>"
  },
  width : {
    type : "int"
  },
  wilsonInterval : {
    type : "boolean"
  },
  xAxisHeight : {
    type : "int"
  },
  xAxisLabelWidth : {
    type : "int"
  },
  xLabelHeight : {
    type : "int"
  },
  xlabel : {
    type : "string"
  },
  xValueParser : {
    type : "function(str)"
  },
  yAxisLabelWidth : {
    type : "int"
  },
  yLabelWidth : {
    type : "int"
  },
  ylabel : {
    type : "string"
  },
  zoomCallback : {
    type : "function(minDate, maxDate, yRanges)"
  }
}; 

