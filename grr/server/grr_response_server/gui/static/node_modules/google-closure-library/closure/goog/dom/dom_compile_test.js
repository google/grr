// Copyright 2016 The Closure Library Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

goog.provide('goog.dom.DomCompileTest');
goog.setTestOnly();


goog.require('goog.dom');
goog.require('goog.dom.TagName');
goog.require('goog.testing.jsunit');


/** Checks types with goog.dom.TagName. */
function testDomTagNameTypes() {
  /** @type {!HTMLAnchorElement} */
  var a = goog.dom.createDom(goog.dom.TagName.A);

  /** @type {!HTMLAnchorElement} */
  var el = goog.dom.createElement(goog.dom.TagName.A);

  /** @type {!IArrayLike<!HTMLAnchorElement>} */
  var anchors = goog.dom.getElementsByTagNameAndClass(goog.dom.TagName.A);

  // Check that goog.dom.HtmlElement is assignable to HTMLElement.
  /** @type {!HTMLElement} */
  var b = goog.dom.createElement(goog.dom.TagName.B);

  /** @type {?HTMLAnchorElement} */
  var anchor = goog.dom.getElementByTagNameAndClass(goog.dom.TagName.A);
}


/** Checks types with goog.dom.TagName. */
function testDomHelperTagNameTypes() {
  var dom = goog.dom.getDomHelper();

  /** @type {!HTMLAnchorElement} */
  var a = dom.createDom(goog.dom.TagName.A);

  /** @type {!HTMLAnchorElement} */
  var el = dom.createElement(goog.dom.TagName.A);

  /** @type {!IArrayLike<!HTMLAnchorElement>} */
  var anchors = dom.getElementsByTagNameAndClass(goog.dom.TagName.A);

  /** @type {?HTMLAnchorElement} */
  var anchor = dom.getElementByTagNameAndClass(goog.dom.TagName.A);
}
