// Copyright 2011 The Closure Library Authors. All Rights Reserved.
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
 * @fileoverview Unit tests for the storage interface.
 *
 */

goog.provide('goog.storage.storage_test');
goog.setTestOnly('goog.storage.storage_test');

goog.require('goog.functions');
goog.require('goog.storage.ErrorCode');
goog.require('goog.storage.Storage');
goog.require('goog.storage.mechanism.mechanismfactory');
goog.require('goog.storage.storageTester');
goog.require('goog.testing.asserts');
goog.require('goog.testing.jsunit');
goog.require('goog.testing.storage.FakeMechanism');

function testBasicOperations() {
  var mechanism = new goog.testing.storage.FakeMechanism();
  var storage = new goog.storage.Storage(mechanism);
  goog.storage.storageTester.runBasicTests(storage);
}

function testMechanismCommunication() {
  var mechanism = new goog.testing.storage.FakeMechanism();
  var storage = new goog.storage.Storage(mechanism);

  // Invalid JSON.
  mechanism.set('first', '');
  assertEquals(goog.storage.ErrorCode.INVALID_VALUE, assertThrows(function() {
                 storage.get('first');
               }));
  mechanism.set('second', '(');
  assertEquals(goog.storage.ErrorCode.INVALID_VALUE, assertThrows(function() {
                 storage.get('second');
               }));

  // Cleaning up.
  storage.remove('first');
  storage.remove('second');
  assertUndefined(storage.get('first'));
  assertUndefined(storage.get('second'));
  assertNull(mechanism.get('first'));
  assertNull(mechanism.get('second'));
}

function testMechanismFailsGracefullyOnInvalidValue() {
  var mechanism = {
    get: goog.functions.error('Invalid value')
  };
  var storage = new goog.storage.Storage(mechanism);
  assertUndefined(storage.get('foobar'));
}
