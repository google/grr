// Copyright 2017 The Closure Library Authors. All Rights Reserved.
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

goog.provide('goog.dom.assertsTest');
goog.setTestOnly('goog.dom.assertsTest');

goog.require('goog.dom.asserts');
goog.require('goog.testing.StrictMock');
goog.require('goog.testing.jsunit');
goog.require('goog.userAgent');


function testAssertIsLocation() {
  assertNotThrows(function() {
    goog.dom.asserts.assertIsLocation(window.location);
  });

  // Ad-hoc mock objects are allowed.
  var o = {foo: 'bar'};
  assertNotThrows(function() {
    goog.dom.asserts.assertIsLocation(o);
  });

  // So are fancy mocks.
  var mock = new goog.testing.StrictMock(window.location);
  assertNotThrows(function() {
    goog.dom.asserts.assertIsLocation(mock);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var linkElement = document.createElement('LINK');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsLocation(linkElement);
    });
    assertContains('Argument is not a Location', ex.message);
  }
}

function testAssertIsHtmlAnchorElement() {
  var anchorElement = document.createElement('A');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLAnchorElement(anchorElement);
  });

  // Ad-hoc mock objects are allowed.
  var o = {foo: 'bar'};
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLAnchorElement(o);
  });
  // So are fancy mocks.
  var mock = new goog.testing.StrictMock(anchorElement);
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLAnchorElement(mock);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('LINK');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLAnchorElement(otherElement);
    });
    assertContains('Argument is not a HTMLAnchorElement', ex.message);
  }
}

function testAssertIsHtmlLinkElement() {
  var linkElement = document.createElement('LINK');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLLinkElement(linkElement);
  });

  // Ad-hoc mock objects are allowed.
  var o = {foo: 'bar'};
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLLinkElement(o);
  });

  // So are fancy mocks.
  var mock = new goog.testing.StrictMock(linkElement);
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLLinkElement(mock);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('A');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLLinkElement(otherElement);
    });
    assertContains('Argument is not a HTMLLinkElement', ex.message);
  }
}

function testAssertIsHtmlImageElement() {
  var imgElement = document.createElement('IMG');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLImageElement(imgElement);
  });

  // Ad-hoc mock objects are allowed.
  var o = {foo: 'bar'};
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLImageElement(o);
  });

  // So are fancy mocks.
  var mock = new goog.testing.StrictMock(imgElement);
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLImageElement(mock);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('SCRIPT');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLImageElement(otherElement);
    });
    assertContains('Argument is not a HTMLImageElement', ex.message);
  }
}

function testAssertIsHtmlEmbedElement() {
  var el = document.createElement('EMBED');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLEmbedElement(el);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('SCRIPT');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLEmbedElement(otherElement);
    });
    assertContains('Argument is not a HTMLEmbedElement', ex.message);
  }
}

function testAssertIsHtmlFrameElement() {
  var el = document.createElement('FRAME');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLFrameElement(el);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('SCRIPT');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLFrameElement(otherElement);
    });
    assertContains('Argument is not a HTMLFrameElement', ex.message);
  }
}

function testAssertIsHtmlIFrameElement() {
  var el = document.createElement('IFRAME');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLIFrameElement(el);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('SCRIPT');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLIFrameElement(otherElement);
    });
    assertContains('Argument is not a HTMLIFrameElement', ex.message);
  }
}

function testAssertIsHtmlObjectElement() {
  var el = document.createElement('OBJECT');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLObjectElement(el);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('SCRIPT');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLObjectElement(otherElement);
    });
    assertContains('Argument is not a HTMLObjectElement', ex.message);
  }
}

function testAssertIsHtmlScriptElement() {
  var el = document.createElement('SCRIPT');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLScriptElement(el);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var otherElement = document.createElement('IMG');
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLScriptElement(otherElement);
    });
    assertContains('Argument is not a HTMLScriptElement', ex.message);
  }
}

function testInOtherWindow() {
  var iframe = document.createElement('IFRAME');
  document.body.appendChild(iframe);
  var el = iframe.contentWindow.document.createElement('SCRIPT');
  assertNotThrows(function() {
    goog.dom.asserts.assertIsHTMLScriptElement(el);
  });

  if (!goog.userAgent.IE || goog.userAgent.isVersionOrHigher(10)) {
    var ex = assertThrows(function() {
      goog.dom.asserts.assertIsHTMLImageElement(el);
    });
    assertContains('Argument is not a HTMLImageElement', ex.message);
  }

  document.body.removeChild(iframe);
}
