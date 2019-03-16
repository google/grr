// Copyright 2015 The Closure Library Authors. All Rights Reserved.
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

goog.provide('goog.net.streams.XhrStreamReaderTest');
goog.setTestOnly('goog.net.streams.XhrStreamReaderTest');

goog.require('goog.net.ErrorCode');
goog.require('goog.net.XmlHttp');
goog.require('goog.net.streams.Base64PbStreamParser');
goog.require('goog.net.streams.JsonStreamParser');
goog.require('goog.net.streams.PbJsonStreamParser');
goog.require('goog.net.streams.PbStreamParser');
goog.require('goog.net.streams.XhrStreamReader');
goog.require('goog.object');
goog.require('goog.testing.asserts');
goog.require('goog.testing.jsunit');
goog.require('goog.testing.net.XhrIo');


var Base64PbStreamParser =
    goog.module.get('goog.net.streams.Base64PbStreamParser');
var PbJsonStreamParser = goog.module.get('goog.net.streams.PbJsonStreamParser');

var xhrReader;
var xhrIo;

var Status = goog.net.streams.XhrStreamReader.Status;
var ReadyState = goog.net.XmlHttp.ReadyState;

var CONTENT_TYPE_HEADER = goog.net.XhrIo.CONTENT_TYPE_HEADER;
var CONTENT_TRANSFER_ENCODING = goog.net.XhrIo.CONTENT_TRANSFER_ENCODING;


function shouldRunTests() {
  return goog.net.streams.XhrStreamReader.isStreamingSupported();
}


function setUp() {
  xhrIo = new goog.testing.net.XhrIo();
  xhrReader = new goog.net.streams.XhrStreamReader(xhrIo);
}


function tearDown() {
  xhrIo = null;
  xhrReader = null;
}


function testGetParserByResponseHeader() {
  xhrIo.getStreamingResponseHeader = function() { return null; };
  assertNull(xhrReader.getParserByResponseHeader_());

  xhrIo.getStreamingResponseHeader = function() { return ''; };
  assertNull(xhrReader.getParserByResponseHeader_());

  xhrIo.getStreamingResponseHeader = function() { return 'xxxxx'; };
  assertNull(xhrReader.getParserByResponseHeader_());

  xhrIo.getStreamingResponseHeader = function(key) {
    if (key == CONTENT_TYPE_HEADER) return 'application/json';
    return null;
  };
  assertTrue(
      xhrReader.getParserByResponseHeader_() instanceof
      goog.net.streams.JsonStreamParser);

  xhrIo.getStreamingResponseHeader = function(key) {
    if (key == CONTENT_TYPE_HEADER) return 'application/json; charset=utf-8';
    return null;
  };
  assertTrue(
      xhrReader.getParserByResponseHeader_() instanceof
      goog.net.streams.JsonStreamParser);

  xhrIo.getStreamingResponseHeader = function(key) {
    if (key == CONTENT_TYPE_HEADER) return 'application/x-protobuf';
    return null;
  };
  assertTrue(
      xhrReader.getParserByResponseHeader_() instanceof
      goog.net.streams.PbStreamParser);

  xhrIo.getStreamingResponseHeader = function(key) {
    if (key == CONTENT_TYPE_HEADER) return 'application/x-protobuf';
    if (key == CONTENT_TRANSFER_ENCODING) return 'BASE64';
    return null;
  };
  assertTrue(
      xhrReader.getParserByResponseHeader_() instanceof Base64PbStreamParser);

  xhrIo.getStreamingResponseHeader = function(key) {
    if (key == CONTENT_TYPE_HEADER) return 'application/json+protobuf';
    return null;
  };
  assertTrue(
      xhrReader.getParserByResponseHeader_() instanceof PbJsonStreamParser);
}


function testNoData() {
  xhrReader.setDataHandler(function(messages) {
    fail('Received unexpected messages: ' + messages);
  });

  var streamStatus = [];
  var httpStatus = [];
  xhrReader.setStatusHandler(function() {
    streamStatus.push(xhrReader.getStatus());
    httpStatus.push(xhrIo.getStatus());
  });

  var headers = {'Content-Type': 'application/json'};
  xhrIo.send('/foo/bar');
  xhrIo.simulateResponse(goog.net.HttpStatus.OK, '', headers);

  assertElementsEquals([Status.NO_DATA], streamStatus);
  assertElementsEquals([goog.net.HttpStatus.OK], httpStatus);
}


function testRetrieveHttpStatusInStatusHandler() {
  var received = [];
  xhrReader.setDataHandler(function(messages) {
    received.push(messages);
  });

  var streamStatus = [];
  var httpStatus = [];
  xhrReader.setStatusHandler(function() {
    console.log('in setStatusHandler');
    streamStatus.push(xhrReader.getStatus());
    httpStatus.push(xhrIo.getStatus());
  });

  var headers = {'Content-Type': 'application/json'};
  xhrIo.send('/foo/bar');
  xhrIo.simulateResponse(goog.net.HttpStatus.OK, '[{"1" : "b"}]', headers);

  assertEquals(1, received.length);
  assertEquals(1, received[0].length);
  assertElementsEquals(['1'], goog.object.getKeys(received[0][0]));
  assertElementsEquals('b', received[0][0][1]);

  assertElementsEquals([Status.ACTIVE, Status.SUCCESS], streamStatus);
  assertElementsEquals(
      [goog.net.HttpStatus.OK, goog.net.HttpStatus.OK], httpStatus);
}


function testParsingSingleMessage() {
  var received = [];
  xhrReader.setDataHandler(function(messages) { received.push(messages); });

  var body = 'CgX__gABdw==';
  var headers = {
    'Content-Type': 'application/x-protobuf',
    'Content-Transfer-Encoding': 'BASE64'
  };
  xhrIo.send('/foo/bar');
  xhrIo.simulateResponse(goog.net.HttpStatus.OK, body, headers);

  assertEquals(1, received.length);
  assertEquals(1, received[0].length);
  assertElementsEquals(['1'], goog.object.getKeys(received[0][0]));
  assertElementsEquals([0xFF, 0xFE, 0x00, 0x01, 0x77], received[0][0][1]);
}


function testParsingMultipleMessages() {
  /**
   * Pass the following protobuf messages
   *    0x0a, 0x03, 0x61, 0x62, 0x63,
   *    0x0a, 0x03, 0x64, 0x65, 0x66,
   *    0x12, 0x03, 0x67, 0x68, 0x69,
   *    0x0a, 0x03, 0x6a, 0x6b, 0x6c,
   */

  var chunk1 = 'CgNh';
  var chunk2 = 'YmMKA';
  var chunk3 = '2RlZhIDZ2hpCg';
  var chunk4 = 'Nqa2w=';

  var received = [];
  xhrReader.setDataHandler(function(messages) { received.push(messages); });

  var headers = {
    'Content-Type': 'application/x-protobuf',
    'Content-Transfer-Encoding': 'BASE64'
  };

  xhrIo.send('/foo/bar');

  xhrIo.simulatePartialResponse(chunk1, headers);
  assertEquals(0, received.length);

  xhrIo.simulatePartialResponse(chunk2);
  assertEquals(1, received.length);
  assertEquals(1, received[0].length);
  assertElementsEquals(['1'], goog.object.getKeys(received[0][0]));
  assertElementsEquals([0x61, 0x62, 0x63], received[0][0][1]);

  received = [];
  xhrIo.simulatePartialResponse(chunk3);
  assertEquals(1, received.length);
  assertEquals(2, received[0].length);
  assertElementsEquals(['1'], goog.object.getKeys(received[0][0]));
  assertElementsEquals([0x64, 0x65, 0x66], received[0][0][1]);
  assertElementsEquals(['2'], goog.object.getKeys(received[0][1]));
  assertElementsEquals([0x67, 0x68, 0x69], received[0][1][2]);

  received = [];
  xhrIo.simulatePartialResponse(chunk4);
  assertEquals(1, received.length);
  assertEquals(1, received[0].length);
  assertElementsEquals(['1'], goog.object.getKeys(received[0][0]));
  assertElementsEquals([0x6a, 0x6b, 0x6c], received[0][0][1]);

  xhrIo.simulateReadyStateChange(ReadyState.COMPLETE);
  assertEquals(Status.SUCCESS, xhrReader.getStatus());
}


function testXhrTimeout() {
  xhrIo.send('/test', null, 'GET', null, null, 1000, false);

  xhrIo.simulatePartialResponse('', {'Content-Type': 'application/x-protobuf'});
  xhrIo.getLastErrorCode = function() { return goog.net.ErrorCode.TIMEOUT; };
  xhrIo.simulateReadyStateChange(ReadyState.COMPLETE);

  assertEquals(Status.TIMEOUT, xhrReader.getStatus());
}


// TODO: more mocked/networked tests, testing.xhrio not useful for streaming
// states
