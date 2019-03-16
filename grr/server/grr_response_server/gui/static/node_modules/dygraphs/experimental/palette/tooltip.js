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
 * @fileoverview Dygraphs options palette tooltip.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
"use strict";

function Tooltip(parent) {
  if (!parent) {
    parent = $("body")[0];
  }
  this.elem = $("<div>")
      .attr("class", "tooltip")
      .appendTo(parent);

  this.title = $("<div>")
      .attr("class", "title")
      .appendTo(this.elem);

  this.type = $("<div>")
      .attr("class", "type")
      .appendTo(this.elem);

  this.body = $("<div>")
      .attr("class", "body")
      .appendTo(this.elem);

  this.hide();
}

Tooltip.prototype.show = function(source, title, type, body) {
  this.title.html(title);
  this.body.html(body);
  this.type.text(type); // textContent for arrays.

  var offset = source.offset();
  this.elem.css({
    "width" : "280",
    "top" : parseInt(offset.top + source[0].offsetHeight) + 'px',
    "left" : parseInt(offset.left + 10) + 'px',
    "visibility" : "visible"});
}

Tooltip.prototype.hide = function() {
  this.elem.css("visibility", "hidden");
}
