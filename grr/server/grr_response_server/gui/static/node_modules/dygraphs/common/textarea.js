// Copyright (c) 2012 Google, Inc.
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
 * @fileoverview Dygraphs options palette text area.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
"use strict";

function TextArea(parent) {
  var body = document.getElementsByTagName("body")[0];
  if (!parent) {
    parent = body;
  }
  this.elem = TextArea.createChild("div", parent, "textarea");
  this.title = TextArea.createChild("div", this.elem, "title");
  this.textarea = TextArea.createChild("textarea", this.elem, "editor");
  this.buttons = TextArea.createChild("div", this.elem, "buttons");
  this.ok = TextArea.createChild("button", this.buttons);
  this.ok.textContent = "OK";
  this.cancel = TextArea.createChild("button", this.buttons);
  this.cancel.textContent = "Cancel";
  this.height = 315;
  this.width = 445;

  var textarea = this;
  this.ok.onclick = function() {
    textarea.hide();
    textarea.okCallback(textarea.textarea.value);
  };
  this.cancel.onclick = function() {
    textarea.hide();
    textarea.cancelCallback();
  };
  this.reposition = function() {
    var left = (document.documentElement.clientWidth - textarea.elem.offsetWidth) / 2;
    var top = (document.documentElement.clientHeight - textarea.elem.offsetHeight) / 2;
    textarea.elem.style.left = Math.max(left, 0) + "px";
    textarea.elem.style.top = Math.max(top, 0) + "px";
  }

  this.background = TextArea.createChild("div", body, "background");
  this.background.id = "modalBackground";
  this.hide();
}

/* I think this is the third place I've copied this function */
TextArea.createChild = function(type, parent, className) {
  var elem = document.createElement(type);
  parent.appendChild(elem);
  if (className) {
    elem.className = className;
  }
  return elem;
};

TextArea.prototype.cancelCallback = function() {
};

TextArea.prototype.okCallback = function(content) {
};

TextArea.prototype.show = function(title, content) {
  this.title.textContent = title;
  this.textarea.value = content;

  var sums = function(adds, subtracts, field) {
    var total = 0;
    for (var idx in adds) {
      total += parseInt(adds[idx][field]);
    }
    for (var idx2 in subtracts) {
      total -= parseInt(subtracts[idx2][field]);
    }
    return total;
  }
  this.elem.style.display = "block";
  this.background.style.display = "block";

  this.elem.style.height = this.height + "px";
  this.elem.style.width = this.width + "px";

  this.textarea.style.height = (-18 + sums([this.elem], [this.title, this.buttons], "offsetHeight")) + "px";
  this.textarea.style.width = (-16 + sums([this.elem], [ ], "offsetWidth")) + "px";

  var textarea = this;

  this.keyDownListener_ = function(event) {
    if(event.keyCode == 13) { // enter / return
      textarea.hide();
    }
    if(event.keyCode == 27) { // esc
      textarea.hide();
    }
  }

  Dygraph.addEvent(document, "keydown", this.keyDownListener_);
  this.reposition();
  window.addEventListener('resize', this.reposition, false);
  document.documentElement.addEventListener('onscroll', this.reposition);
}

TextArea.prototype.hide = function() {
  Dygraph.removeEvent(document, "keypress", this.keyDownListener_);
  this.keyDownListener_ = null;
  this.elem.style.display = "none";
  this.background.style.display = "none";
  window.removeEventListener("resize", this.reposition);
  document.documentElement.removeEventListener("onscroll", this.reposition);
}
