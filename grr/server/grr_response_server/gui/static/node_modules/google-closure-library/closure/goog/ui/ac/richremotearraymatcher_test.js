// Copyright 2009 The Closure Library Authors. All Rights Reserved.
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

goog.provide('goog.ui.ac.RichRemoteArrayMatcherTest');
goog.setTestOnly('goog.ui.ac.RichRemoteArrayMatcherTest');

goog.require('goog.net.XhrIo');
goog.require('goog.testing.MockControl');
goog.require('goog.testing.jsunit');
goog.require('goog.testing.net.XhrIo');
goog.require('goog.ui.ac.RichRemoteArrayMatcher');

var url = 'http://www.google.com';
var token = 'goog';
var maxMatches = 5;

var responseJsonText = '[["type1", "eric", "larry", "sergey"]]';
var responseJsonType1 = ["eric", "larry", "sergey"];

var mockControl;
var mockMatchHandler;


function setUp() {
  goog.net.XhrIo = goog.testing.net.XhrIo;
  mockControl = new goog.testing.MockControl();
  mockMatchHandler = mockControl.createFunctionMock();
}

/**
 * Callback for type1 responses.
 * @param {string} response
 * @return {string}
 */
function type1(response) {
  return response;
}

function testRequestMatchingRows() {
  var matcher = new goog.ui.ac.RichRemoteArrayMatcher(url);
  mockMatchHandler(token, responseJsonType1);
  mockControl.$replayAll();
  matcher.requestMatchingRows(token, maxMatches, mockMatchHandler);
  matcher.xhr_.simulateResponse(200, responseJsonText);
  mockControl.$verifyAll();
  mockControl.$resetAll();
}

function testSetRowBuilder() {
  var matcher = new goog.ui.ac.RichRemoteArrayMatcher(url);
  matcher.setRowBuilder(function(type, response) {
    assertEquals("type1", type);
    return response;
  });
  mockMatchHandler(token, responseJsonType1);
  mockControl.$replayAll();
  matcher.requestMatchingRows(token, maxMatches, mockMatchHandler);
  matcher.xhr_.simulateResponse(200, responseJsonText);
  mockControl.$verifyAll();
  mockControl.$resetAll();
}
