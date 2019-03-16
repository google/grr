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

goog.module('goog.net.streams.PbJsonStreamParserTest');
goog.setTestOnly('goog.net.streams.PbJsonStreamParserTest');

var PbJsonStreamParser = goog.require('goog.net.streams.PbJsonStreamParser');
var object = goog.require('goog.object');
var testSuite = goog.require('goog.testing.testSuite');


/**
 * @param {!Array<!Object>} result The result to check
 * @param {number} numMessages The expected number of messages
 */
function assertMessages(result, numMessages) {
  assertEquals(numMessages, result.length);
  for (var i = 0; i < numMessages; i++) {
    assertElementsEquals(['1'], object.getKeys(result[i]));
  }
}


/**
 * @param {!Array<!Object>} result The result to check
 * @param {number} numMessages The expected number of messages
 */
function assertMessagesAndStatus(result, numMessages) {
  assertEquals(numMessages, result.length - 1);
  for (var i = 0; i < numMessages; i++) {
    assertElementsEquals(['1'], object.getKeys(result[i]));
  }
  assertElementsEquals(['2'], object.getKeys(result[result.length - 1]));
}


testSuite({
  testEmptyStream: function() {
    var parser = new PbJsonStreamParser();
    assertNull(parser.parse(' [ ] '));
  },

  testSingleMessage: function() {
    var parser = new PbJsonStreamParser();
    var result = parser.parse('[  [[null,1,2,null, "a,b[]]]"]]  ]');
    assertMessages(result, 1);
    assertEquals('[null,1,2,null, "a,b[]]]"]', result[0][1]);
  },

  testMultipleMessages: function() {
    var parser = new PbJsonStreamParser();
    var msgs = '[[1,2]  ,  [3,4],[{"a": "xyz"}]]';
    var result = parser.parse('[' + msgs + ']');
    assertMessages(result, 3);
    assertEquals('[1,2]', result[0][1]);
    assertEquals('  [3,4]', result[1][1]);
    assertEquals('[{"a": "xyz"}]', result[2][1]);
  },

  testMultipleMessagesInChunks: function() {
    var parser = new PbJsonStreamParser();
    var input1 = '[[[1,2]';
    var input2 = '  ,  [3,4';
    var input3 = '],[{"a": "xyz"}]]]';

    var result = parser.parse(input1);
    assertMessages(result, 1);
    assertEquals('[1,2]', result[0][1]);

    result = parser.parse(input2);
    assertNull(result);

    result = parser.parse(input3);
    assertMessages(result, 2);
    assertEquals('  [3,4]', result[0][1]);
    assertEquals('[{"a": "xyz"}]', result[1][1]);
  },

  testOnlyStatus: function() {
    var parser = new PbJsonStreamParser();
    var status = '[1,null,"abced",[true,false]]';
    var result = parser.parse('[null,' + status + ']');
    assertMessagesAndStatus(result, 0);
    assertEquals(status, result[0][2]);
  },

  testMessagesAndStatus: function() {
    var parser = new PbJsonStreamParser();
    var msgs = '[[1, null, 2], ["a", true],[]]';
    var status = '["400", "error", "bad request", {"details": null}]';
    var result = parser.parse('[' + msgs + ',' + status + ']');
    assertMessagesAndStatus(result, 3);
    assertEquals('[1, null, 2]', result[0][1]);
    assertEquals(' ["a", true]', result[1][1]);
    assertEquals('[]', result[2][1]);
    assertEquals(
        '["400", "error", "bad request", {"details": null}]', result[3][2]);
  },

  testMessagesAndStatusInChunks: function() {
    var parser = new PbJsonStreamParser();
    var input1 = '[[[1, null, 2], ["a", ';
    var input2 = 'true]], [';
    var input3 = '"error"]';
    var input4 = ']';

    var result = parser.parse(input1);
    assertMessages(result, 1);
    assertEquals('[1, null, 2]', result[0][1]);

    result = parser.parse(input2);
    assertMessages(result, 1);
    assertEquals(' ["a", true]', result[0][1]);

    result = parser.parse(input3);
    assertMessagesAndStatus(result, 0);
    assertEquals('["error"]', result[0][2]);

    result = parser.parse(input4);
    assertNull(result);
  },

  testInvalidInputs: function() {
    var parser1 = new PbJsonStreamParser();
    // Invalid JSON
    assertThrows(function() {
      parser1.parse('[[["a":"b"]]]');
    });
    // Stream already broken
    assertThrows(function() {
      parser1.parse('[');
    });

    var parser2 = new PbJsonStreamParser();
    parser2.parse('[ [[1, 2]], ["error"] ]');
    // Extra input
    assertThrows(function() {
      parser2.parse(',');
    });

    var parser3 = new PbJsonStreamParser();
    // Extra element of the wrapping array
    assertThrows(function() {
      parser3.parse('[ [[1, 2]], ["error"], ["error"] ]');
    });

    var parser4 = new PbJsonStreamParser();
    // Extra element of the wrapping array in chunks
    var result = parser4.parse('[ [[1, 2]], ["error"]');
    assertMessagesAndStatus(result, 1);
    assertEquals('[1, 2]', result[0][1]);
    assertEquals('["error"]', result[1][2]);
    assertThrows(function() {
      parse4.parse(', ["error"]');
    });
  }
});
