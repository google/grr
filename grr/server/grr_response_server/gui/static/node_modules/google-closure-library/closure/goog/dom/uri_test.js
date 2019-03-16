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

goog.module('goog.dom.uriTest');
goog.setTestOnly();

var testSuite = goog.require('goog.testing.testSuite');
var uri = goog.require('goog.dom.uri');

testSuite({
   testMethod: function() {
             var baseUri = uri.normalizeUri('/');
             assertEquals(baseUri + 'foo', uri.normalizeUri('/foo'));
             assertEquals(baseUri + 'foo', uri.normalizeUri('/bar/../foo'));
             assertEquals(
                 'javascript:test', uri.normalizeUri('javascript:test'));
             assertEquals(
                 'https://google.com/test',
                 uri.normalizeUri('https://google.com/test'));
           },
});
