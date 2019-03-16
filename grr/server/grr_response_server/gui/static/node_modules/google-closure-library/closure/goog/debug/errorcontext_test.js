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

goog.module('goog.debug.errorcontextTest');
goog.setTestOnly('goog.debug.errorcontextTest');

const errorcontext = goog.require('goog.debug.errorcontext');
const testSuite = goog.require('goog.testing.testSuite');
goog.require('goog.testing.jsunit');

testSuite({
  testAddContext() {
    const err = new Error('something happened');
    assertObjectEquals({}, errorcontext.getErrorContext(err));

    errorcontext.addErrorContext(err, 'key', 'value');
    assertObjectEquals({key: 'value'}, errorcontext.getErrorContext(err));

    errorcontext.addErrorContext(err, 'another_key', 'another_value');
    assertObjectEquals(
        {key: 'value', another_key: 'another_value'},
        errorcontext.getErrorContext(err));

    // Overwrite the first context value.
    errorcontext.addErrorContext(err, 'key', 'new_value');
    assertObjectEquals(
        {key: 'new_value', another_key: 'another_value'},
        errorcontext.getErrorContext(err));
  },
});
