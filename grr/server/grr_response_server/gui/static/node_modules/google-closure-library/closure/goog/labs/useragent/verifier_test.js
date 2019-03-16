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

/**
 * @fileoverview Description of this file.
 */
goog.module('goog.labs.useragent.verifierTest');
goog.setTestOnly();

var testSuite = goog.require('goog.testing.testSuite');
var browser = goog.require('goog.labs.userAgent.browser');
var verifier = goog.require('goog.labs.useragent.verifier');


testSuite({
  testIEVersion: function() {
    var isUserAgentIE = browser.isIE();
    var versionByBehavior = verifier.detectIeVersionByBehavior();
    var versionByNavigator = verifier.detectIeVersionByNavigator();
    var correctedVersion = verifier.getCorrectedIEVersionByNavigator();

    if (isUserAgentIE) {
      var version = Number(browser.getVersion());
      assertEquals('behavior detection incorrect', version, versionByBehavior);
      if (version != 11) {
        assertEquals(
            'navigator version incorrect', version, versionByNavigator);
      } else {
        // IE 11 doesn't want to be detected as IE
        assertEquals('navigator version incorrect', 0, versionByNavigator);
      }
      assertEquals('corrected version incorrect', version, correctedVersion);
    } else {
      assertEquals(0, versionByBehavior);
    }
  },
});
