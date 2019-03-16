// Copyright 2013 The Closure Library Authors. All Rights Reserved.
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

/**
 * @fileoverview Unit tests for goog.dom.safe.
 */

goog.provide('goog.dom.safeTest');
goog.setTestOnly('goog.dom.safeTest');

goog.require('goog.asserts');
goog.require('goog.dom.safe');
goog.require('goog.dom.safe.InsertAdjacentHtmlPosition');
goog.require('goog.html.SafeHtml');
goog.require('goog.html.SafeScript');
goog.require('goog.html.SafeStyle');
goog.require('goog.html.SafeUrl');
goog.require('goog.html.TrustedResourceUrl');
goog.require('goog.html.testing');
goog.require('goog.string');
goog.require('goog.string.Const');
goog.require('goog.testing');
goog.require('goog.testing.jsunit');
goog.require('goog.userAgent');


var mockWindowOpen;


function tearDown() {
  if (mockWindowOpen) {
    mockWindowOpen.$tearDown();
  }
}


function testInsertAdjacentHtml() {
  var writtenHtml;
  var writtenPosition;
  var mockNode = /** @type {!Node} */ ({
    'insertAdjacentHTML': function(position, html) {
      writtenPosition = position;
      writtenHtml = html;
    }
  });

  goog.dom.safe.insertAdjacentHtml(
      mockNode, goog.dom.safe.InsertAdjacentHtmlPosition.BEFOREBEGIN,
      goog.html.SafeHtml.create('div', {}, 'foobar'));
  assertEquals('<div>foobar</div>', writtenHtml);
  assertEquals('beforebegin', writtenPosition);
}


function testSetInnerHtml() {
  var mockElement =
      /** @type {!Element} */ ({'tagName': 'DIV', 'innerHTML': 'blarg'});
  var html = '<script>somethingTrusted();<' +
      '/script>';
  var safeHtml = goog.html.testing.newSafeHtmlForTest(html);
  goog.dom.safe.setInnerHtml(mockElement, safeHtml);
  assertEquals(html, mockElement.innerHTML);
}

function testSetInnerHtml_doesntAllowScript() {
  var script =
      /** @type {!Element} */ ({'tagName': 'SCRIPT', 'innerHTML': 'blarg'});
  var safeHtml = goog.html.SafeHtml.htmlEscape('alert(1);');
  assertThrows(function() { goog.dom.safe.setInnerHtml(script, safeHtml); });
}

function testSetInnerHtml_doesntAllowStyle() {
  var style =
      /** @type {!Element} */ ({'tagName': 'STYLE', 'innerHTML': 'blarg'});
  var safeHtml = goog.html.SafeHtml.htmlEscape('A { color: red; }');
  assertThrows(function() { goog.dom.safe.setInnerHtml(style, safeHtml); });
}

function testSetStyle() {
  var style =
      goog.html.SafeStyle.fromConstant(goog.string.Const.from('color: red;'));
  var elem = document.createElement('div');
  assertEquals('', elem.style.color);  // sanity check

  goog.dom.safe.setStyle(elem, style);
  assertEquals('red', elem.style.color);
}

function testDocumentWrite() {
  var mockDoc = /** @type {!Document} */ ({
    'html': null,
    /** @suppress {globalThis} */
    'write': function(html) { this['html'] = html; }
  });
  var html = '<script>somethingTrusted();<' +
      '/script>';
  var safeHtml = goog.html.testing.newSafeHtmlForTest(html);
  goog.dom.safe.documentWrite(mockDoc, safeHtml);
  assertEquals(html, mockDoc.html);
}


function testsetLinkHrefAndRel_trustedResourceUrl() {
  var mockLink = /** @type {!HTMLLinkElement} */ ({'href': null, 'rel': null});

  var url = goog.html.TrustedResourceUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  // Test case-insensitive too.
  goog.dom.safe.setLinkHrefAndRel(mockLink, url, 'foo, Stylesheet, bar');
  assertEquals('javascript:trusted();', mockLink.href);

  goog.dom.safe.setLinkHrefAndRel(mockLink, url, 'foo, bar');
  assertEquals('javascript:trusted();', mockLink.href);
}


function testsetLinkHrefAndRel_safeUrl() {
  var mockLink = /** @type {!HTMLLinkElement} */ ({'href': null, 'rel': null});

  var url = goog.html.SafeUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  assertThrows(function() {
    goog.dom.safe.setLinkHrefAndRel(mockLink, url, 'foo, stylesheet, bar');
  });

  goog.dom.safe.setLinkHrefAndRel(mockLink, url, 'foo, bar');
  assertEquals('javascript:trusted();', mockLink.href);
}


function testsetLinkHrefAndRel_string() {
  var mockLink = /** @type {!HTMLLinkElement} */ ({'href': null, 'rel': null});

  assertThrows(function() {
    goog.dom.safe.setLinkHrefAndRel(
        mockLink, 'javascript:evil();', 'foo, stylesheet, bar');
  });
  withAssertionFailure(function() {
    goog.dom.safe.setLinkHrefAndRel(mockLink, 'javascript:evil();', 'foo, bar');
  });
  assertEquals('about:invalid#zClosurez', mockLink.href);
}

function testsetLinkHrefAndRel_assertsType() {
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('A');
    var ex = assertThrows(function() {
      goog.dom.safe.setLinkHrefAndRel(
          /** @type {!HTMLLinkElement} */ (otherElement), 'http://example.com/',
          'author');
    });
    assert(
        goog.string.contains(ex.message, 'Argument is not a HTMLLinkElement'));
  }
}

/**
 * Returns a link element, incorrectly typed as a Location.
 * @return {!Location}
 * @suppress {checkTypes}
 */
function makeLinkElementTypedAsLocation() {
  return document.createElement('LINK');
}

function testSetLocationHref() {
  var mockLoc = /** @type {!Location} */ ({'href': 'blarg'});
  withAssertionFailure(function() {
    goog.dom.safe.setLocationHref(mockLoc, 'javascript:evil();');
  });
  assertEquals('about:invalid#zClosurez', mockLoc.href);

  mockLoc = /** @type {!Location} */ ({'href': 'blarg'});
  var safeUrl = goog.html.SafeUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  goog.dom.safe.setLocationHref(mockLoc, safeUrl);
  assertEquals('javascript:trusted();', mockLoc.href);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var ex = assertThrows(function() {
      goog.dom.safe.setLocationHref(makeLinkElementTypedAsLocation(), safeUrl);
    });
    assert(goog.string.contains(ex.message, 'Argument is not a Location'));
  }
}


function testSetAnchorHref() {
  var anchor = /** @type {!HTMLAnchorElement} */ (document.createElement('A'));
  withAssertionFailure(function() {
    goog.dom.safe.setAnchorHref(anchor, 'javascript:evil();');
  });
  assertEquals('about:invalid#zClosurez', anchor.href);

  anchor = /** @type {!HTMLAnchorElement} */ (document.createElement('A'));
  var safeUrl = goog.html.SafeUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  goog.dom.safe.setAnchorHref(anchor, safeUrl);
  assertEquals('javascript:trusted();', anchor.href);

  // Works with mocks too.
  var mockAnchor = /** @type {!HTMLAnchorElement} */ ({'href': 'blarg'});
  withAssertionFailure(function() {
    goog.dom.safe.setAnchorHref(mockAnchor, 'javascript:evil();');
  });
  assertEquals('about:invalid#zClosurez', mockAnchor.href);

  mockAnchor = /** @type {!HTMLAnchorElement} */ ({'href': 'blarg'});
  safeUrl = goog.html.SafeUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  goog.dom.safe.setAnchorHref(mockAnchor, safeUrl);
  assertEquals('javascript:trusted();', mockAnchor.href);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('LINK');
    var ex = assertThrows(function() {
      goog.dom.safe.setAnchorHref(
          /** @type {!HTMLAnchorElement} */ (otherElement), safeUrl);
    });
    assert(goog.string.contains(
        ex.message, 'Argument is not a HTMLAnchorElement'));
  }
}

function testSetImageSrc_withSafeUrlObject() {
  var mockImageElement = /** @type {!HTMLImageElement} */ ({'src': 'blarg'});
  withAssertionFailure(function() {
    goog.dom.safe.setImageSrc(mockImageElement, 'javascript:evil();');
  });
  assertEquals('about:invalid#zClosurez', mockImageElement.src);

  mockImageElement = /** @type {!HTMLImageElement} */ ({'src': 'blarg'});
  var safeUrl = goog.html.SafeUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  goog.dom.safe.setImageSrc(mockImageElement, safeUrl);
  assertEquals('javascript:trusted();', mockImageElement.src);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('SCRIPT');
    var ex = assertThrows(function() {
      goog.dom.safe.setImageSrc(
          /** @type {!HTMLImageElement} */ (otherElement), safeUrl);
    });
    assert(
        goog.string.contains(ex.message, 'Argument is not a HTMLImageElement'));
  }
}

function testSetImageSrc_withHttpsUrl() {
  var mockImageElement = /** @type {!HTMLImageElement} */ ({'src': 'blarg'});

  var safeUrl = 'https://trusted_url';
  goog.dom.safe.setImageSrc(mockImageElement, safeUrl);
  assertEquals(safeUrl, mockImageElement.src);
}

function testSetEmbedSrc() {
  var url = goog.html.TrustedResourceUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  var mockElement = /** @type {!HTMLEmbedElement} */ ({'src': 'blarg'});
  goog.dom.safe.setEmbedSrc(mockElement, url);
  assertEquals('javascript:trusted();', mockElement.src);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('IMAGE');
    var ex = assertThrows(function() {
      goog.dom.safe.setEmbedSrc(
          /** @type {!HTMLEmbedElement} */ (otherElement), url);
    });
    assert(
        goog.string.contains(ex.message, 'Argument is not a HTMLEmbedElement'));
  }
}

function testSetFrameSrc() {
  var url = goog.html.TrustedResourceUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  var mockElement = /** @type {!HTMLFrameElement} */ ({'src': 'blarg'});
  goog.dom.safe.setFrameSrc(mockElement, url);
  assertEquals('javascript:trusted();', mockElement.src);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('IMAGE');
    var ex = assertThrows(function() {
      goog.dom.safe.setFrameSrc(
          /** @type {!HTMLFrameElement} */ (otherElement), url);
    });
    assert(
        goog.string.contains(ex.message, 'Argument is not a HTMLFrameElement'));
  }
}

function testSetIframeSrc() {
  var url = goog.html.TrustedResourceUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  var mockElement = /** @type {!HTMLIFrameElement} */ ({'src': 'blarg'});
  goog.dom.safe.setIframeSrc(mockElement, url);
  assertEquals('javascript:trusted();', mockElement.src);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('IMAGE');
    var ex = assertThrows(function() {
      goog.dom.safe.setIframeSrc(
          /** @type {!HTMLIFrameElement} */ (otherElement), url);
    });
    assert(goog.string.contains(
        ex.message, 'Argument is not a HTMLIFrameElement'));
  }
}

function testSetIframeSrcdoc() {
  var html = goog.html.SafeHtml.create('div', {}, 'foobar');
  var mockIframe = /** @type {!HTMLIFrameElement} */ ({'srcdoc': ''});
  goog.dom.safe.setIframeSrcdoc(mockIframe, html);
  assertEquals('<div>foobar</div>', mockIframe.srcdoc);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('IMAGE');
    var ex = assertThrows(function() {
      goog.dom.safe.setIframeSrcdoc(
          /** @type {!HTMLIFrameElement} */ (otherElement), html);
    });
    assert(goog.string.contains(
        ex.message, 'Argument is not a HTMLIFrameElement'));
  }
}

function testSetObjectData() {
  var url = goog.html.TrustedResourceUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  var mockElement = /** @type {!HTMLObjectElement} */ ({'data': 'blarg'});
  goog.dom.safe.setObjectData(mockElement, url);
  assertEquals('javascript:trusted();', mockElement.data);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('IMAGE');
    var ex = assertThrows(function() {
      goog.dom.safe.setObjectData(
          /** @type {!HTMLObjectElement} */ (otherElement), url);
    });
    assert(goog.string.contains(
        ex.message, 'Argument is not a HTMLObjectElement'));
  }
}

function testSetScriptSrc() {
  var url = goog.html.TrustedResourceUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  var mockElement = /** @type {!HTMLScriptElement} */ ({'src': 'blarg'});
  goog.dom.safe.setScriptSrc(mockElement, url);
  assertEquals('javascript:trusted();', mockElement.src);

  // Asserts correct runtime type.
  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('IMAGE');
    var ex = assertThrows(function() {
      goog.dom.safe.setScriptSrc(
          /** @type {!HTMLScriptElement} */ (otherElement), url);
    });
    assert(goog.string.contains(
        ex.message, 'Argument is not a HTMLScriptElement'));
  }
}

function testSetScriptContent() {
  var mockScriptElement = /** @type {!HTMLScriptElement} */ ({});

  var content =
      goog.html.SafeScript.fromConstant(goog.string.Const.from('alert(1);'));
  goog.dom.safe.setScriptContent(mockScriptElement, content);
  assertEquals(goog.html.SafeScript.unwrap(content), mockScriptElement.text);
}

function testOpenInWindow() {
  mockWindowOpen =
      /** @type {?} */ (goog.testing.createMethodMock(window, 'open'));
  var fakeWindow = {};

  mockWindowOpen('about:invalid#zClosurez', 'name', 'specs', true)
      .$returns(fakeWindow);
  mockWindowOpen.$replay();
  var retVal = withAssertionFailure(function() {
    return goog.dom.safe.openInWindow(
        'javascript:evil();', window, goog.string.Const.from('name'), 'specs',
        true);
  });
  mockWindowOpen.$verify();
  assertEquals(
      'openInWindow should return the created window', fakeWindow, retVal);

  mockWindowOpen.$reset();
  retVal = null;

  var safeUrl = goog.html.SafeUrl.fromConstant(
      goog.string.Const.from('javascript:trusted();'));
  mockWindowOpen('javascript:trusted();', 'name', 'specs', true)
      .$returns(fakeWindow);
  mockWindowOpen.$replay();
  retVal = goog.dom.safe.openInWindow(
      safeUrl, window, goog.string.Const.from('name'), 'specs', true);
  mockWindowOpen.$verify();
  assertEquals(
      'openInWindow should return the created window', fakeWindow, retVal);
}

/**
 * Tests that f raises an AssertionError and runs f while disabling assertion
 * errors.
 *
 * @param {function():*} f function with a failing assertion.
 * @return {*} the return value of f.
 */
function withAssertionFailure(f) {
  assertThrows(f);
  goog.asserts.setErrorHandler(function(error) {});
  try {
    return f();
  } finally {
    goog.asserts.setErrorHandler(goog.asserts.DEFAULT_ERROR_HANDLER);
  }
}
