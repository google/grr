// Copyright 2012 The Closure Library Authors. All Rights Reserved.
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

goog.module('goog.async.AnimationDelayTest');
goog.setTestOnly('goog.async.AnimationDelayTest');

var AnimationDelay = goog.require('goog.async.AnimationDelay');
var Promise = goog.require('goog.Promise');
var PropertyReplacer = goog.require('goog.testing.PropertyReplacer');
var Timer = goog.require('goog.Timer');
var jsunit = goog.require('goog.testing.jsunit');
var testSuite = goog.require('goog.testing.testSuite');

var TEST_DELAY = 50;
var stubs = new PropertyReplacer();

testSuite({
  tearDown: function() { stubs.reset(); },

  testStart: function() {
    var resolver = Promise.withResolver();
    var start = goog.now();
    var delay = new AnimationDelay(function(end) {
      assertNotNull(resolver);  // fail if called multiple times
      resolver.resolve();
      resolver = null;
    });

    delay.start();

    return resolver.promise;
  },

  testStop: function() {
    var resolver = Promise.withResolver();
    var start = goog.now();
    var delay = new AnimationDelay(function(end) { resolver.reject(); });

    delay.start();
    delay.stop();

    return Timer.promise(TEST_DELAY).then(function() {
      resolver.resolve();
      return resolver.promise;
    });
  },

  testAlwaysUseGoogNowForHandlerTimestamp: function() {
    var resolver = Promise.withResolver();
    var expectedValue = 12345.1;
    stubs.set(goog, 'now', function() { return expectedValue; });

    var delay = new AnimationDelay(function(timestamp) {
      assertEquals(expectedValue, timestamp);
      resolver.resolve();
    });

    delay.start();

    return resolver.promise;
  },

  testStartIfActive: function() {
    var delay = new AnimationDelay(goog.nullFunction);
    delay.start();

    var startWasCalled = false;
    stubs.set(AnimationDelay.prototype, 'start', function() {
      startWasCalled = true;
    });

    delay.startIfNotActive();
    assertEquals(startWasCalled, false);
    delay.stop();
    delay.startIfNotActive();
    assertEquals(startWasCalled, true);
  }
});
