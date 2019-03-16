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
 * @fileoverview Utility functions for Dygraphs.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
var DygraphOps = {};

DygraphOps.defaultEvent_ = {
  type : '',
  canBubble : true,
  cancelable : true,
  view : document.defaultView,
  detail : 0,
  screenX : 0,
  screenY : 0,
  clientX : 0,
  clientY : 0,
  ctrlKey : false,
  altKey : false,
  shiftKey : false,
  metaKey : false,
  button : 0,
  relatedTarget : null
};

/**
 * Create an event. Sets default event values except for special ones
 * overridden by the 'custom' parameter.
 *
 * @param command the command to create.
 * @param custom an associative array of event attributes and their new values.
 */
DygraphOps.createEvent = function(command, custom) {

  var copy = function(from, to) {
    if (from != null) {
      for (var prop in from) {
        if(from.hasOwnProperty(prop)) {
          to[prop] = from[prop];
        }
      }
    }
  }

  var e = {};
  copy(DygraphOps.defaultEvent_, e);
  copy(command, e);
  copy(custom, e);

  var event = document.createEvent('MouseEvents');
  event.initMouseEvent(
    e.type,
    e.canBubble,
    e.cancelable,
    e.view, 
    e.detail,
    e.screenX,
    e.screenY,
    e.clientX,
    e.clientY,
    e.ctrlKey,
    e.altKey,
    e.shiftKey,
    e.metaKey,
    e.button,
    e.relatedTarget);
  return event;
};

/**
 * Dispatch an event onto the graph's canvas.
 */
DygraphOps.dispatchCanvasEvent = function(g, event) {
  g.canvas_.dispatchEvent(event);
};

DygraphOps.dispatchDoubleClick = function(g, custom) {
  var opts = {
    type : 'dblclick',
    detail : 2
  };
  var event = DygraphOps.createEvent(opts, custom);
  DygraphOps.dispatchCanvasEvent(g, event);
};

/*
 * Create an 'opts' argument which can be passed to createEvent that contains
 * type, screenX, screenY, clientX, clientY.
 */
DygraphOps.createOptsForPoint_ = function(g, type, x, y) {
  var pos = Dygraph.findPos(g.canvas_);
  var pageX = pos.x + x;
  var pageY = pos.y + y;

  return {
    type : type,
    screenX : pageX,
    screenY : pageY,
    clientX : pageX,
    clientY : pageY,
  };
};

DygraphOps.dispatchMouseDown_Point = function(g, x, y, custom) {
  var opts = DygraphOps.createOptsForPoint_(g, 'mousedown', x, y);
  opts.detail = 1;
  var event = DygraphOps.createEvent(opts, custom);
  DygraphOps.dispatchCanvasEvent(g, event);
};

DygraphOps.dispatchMouseMove_Point = function(g, x, y, custom) {
  var opts = DygraphOps.createOptsForPoint_(g, 'mousemove', x, y);
  var event = DygraphOps.createEvent(opts, custom);
  DygraphOps.dispatchCanvasEvent(g, event);
};

DygraphOps.dispatchMouseUp_Point = function(g, x, y, custom) {
  var opts = DygraphOps.createOptsForPoint_(g, 'mouseup', x, y);
  var event = DygraphOps.createEvent(opts, custom);
  DygraphOps.dispatchCanvasEvent(g, event);
};

DygraphOps.dispatchMouseOver_Point = function(g, x, y, custom) {
  var opts = DygraphOps.createOptsForPoint_(g, 'mouseover', x, y);
  var event = DygraphOps.createEvent(opts, custom);
  DygraphOps.dispatchCanvasEvent(g, event);
};

DygraphOps.dispatchMouseOut_Point = function(g, x, y, custom) {
  var opts = DygraphOps.createOptsForPoint_(g, 'mouseout', x, y);
  var event = DygraphOps.createEvent(opts, custom);
  DygraphOps.dispatchCanvasEvent(g, event);
};

/**
 * Dispatches a mouse down using the graph's data coordinate system.
 * (The y value mapped to the first axis.)
 */
DygraphOps.dispatchMouseDown = function(g, x, y, custom) {
  DygraphOps.dispatchMouseDown_Point(
      g,
      g.toDomXCoord(x),
      g.toDomYCoord(y),
      custom);
};

/**
 * Dispatches a mouse move using the graph's data coordinate system.
 * (The y value mapped to the first axis.)
 */
DygraphOps.dispatchMouseMove = function(g, x, y, custom) {
  DygraphOps.dispatchMouseMove_Point(
      g,
      g.toDomXCoord(x),
      g.toDomYCoord(y),
      custom);
};

/**
 * Dispatches a mouse up using the graph's data coordinate system.
 * (The y value mapped to the first axis.)
 */
DygraphOps.dispatchMouseUp = function(g, x, y, custom) {
  DygraphOps.dispatchMouseUp_Point(
      g,
      g.toDomXCoord(x),
      g.toDomYCoord(y),
      custom);
};

/**
 * Dispatches a mouse over using the graph's data coordinate system.
 * (The y value mapped to the first axis.)
 */
DygraphOps.dispatchMouseOver = function(g, x, y, custom) {
  DygraphOps.dispatchMouseOver_Point(
      g,
      g.toDomXCoord(x),
      g.toDomYCoord(y),
      custom);
};

/**
 * Dispatches a mouse out using the graph's data coordinate system.
 * (The y value mapped to the first axis.)
 */
DygraphOps.dispatchMouseOut = function(g, x, y, custom) {
  DygraphOps.dispatchMouseOut_Point(
      g,
      g.toDomXCoord(x),
      g.toDomYCoord(y),
      custom);
};

