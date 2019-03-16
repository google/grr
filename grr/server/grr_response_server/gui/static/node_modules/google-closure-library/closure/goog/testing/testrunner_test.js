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

goog.provide('goog.testing.TestRunnerTest');
goog.setTestOnly();

goog.require('goog.testing.TestCase');
goog.require('goog.testing.TestRunner');
goog.require('goog.testing.asserts');
goog.require('goog.testing.jsunit');


let testRunner;
let testCase;

function setUp() {
  testRunner = new goog.testing.TestRunner();
  testCase = new goog.testing.TestCase();
}

function testInitialize() {
  assert(!testRunner.isInitialized());
  testRunner.initialize(testCase);
  assert(testRunner.isInitialized());
}

function testIsFinished() {
  testRunner.initialize(testCase);
  assert(!testRunner.isFinished());
  testRunner.logError('oops');
  assert(testRunner.isFinished());
}

function testGetUniqueId() {
  // We only really care that this string is unique to instances.
  const anotherRunner = new goog.testing.TestRunner();
  assert(anotherRunner.getUniqueId() != testRunner.getUniqueId());
}
