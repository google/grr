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

goog.provide('goog.testing.fs.BlobTest');
goog.setTestOnly('goog.testing.fs.BlobTest');

goog.require('goog.dom');
goog.require('goog.testing.fs.Blob');
goog.require('goog.testing.jsunit');

var hasArrayBuffer = goog.isDef(goog.global.ArrayBuffer);

function testInput() {
  var blob = new goog.testing.fs.Blob();
  assertEquals('', blob.toString());
  assertEquals(0, blob.size);

  // input is a string
  blob = new goog.testing.fs.Blob('資');
  assertEquals('資', blob.toString());
  assertEquals(3, blob.size);

  if (!hasArrayBuffer) {
    return;
  }

  // input is an Array of Arraybuffer.
  // decimal code for e8 b3 87, that's 資 in UTF-8
  blob = new goog.testing.fs.Blob([new Uint8Array([232, 179, 135])]);
  assertEquals('資', blob.toString());
  assertEquals(3, blob.size);

  // input is an Array of Arraybuffer with control characters.
  var data = goog.dom.getWindow().atob('iVBORw0KGgo=');
  var arr = [];
  for (var i = 0; i < data.length; i++) {
    arr.push(data.charCodeAt(i));
  }
  blob = new goog.testing.fs.Blob([new Uint8Array(arr)]);
  assertArrayEquals([137, 80, 78, 71, 13, 10, 26, 10], blob.data_);
  assertEquals(8, blob.size);

  // input is an Array of strings
  blob = new goog.testing.fs.Blob(['資', 'é']);
  assertEquals('資é', blob.toString());
  assertEquals(5, blob.size);

  // input is an Array of Arraybuffer + string
  blob = new goog.testing.fs.Blob([new Uint8Array([232, 179, 135]), 'é']);
  assertEquals('資é', blob.toString());
  assertEquals(5, blob.size);
}

function testType() {
  var blob = new goog.testing.fs.Blob();
  assertEquals('', blob.type);

  blob = new goog.testing.fs.Blob('foo bar baz', 'text/plain');
  assertEquals('text/plain', blob.type);
}

function testSlice() {
  var blob = new goog.testing.fs.Blob('abcdef');
  assertEquals('bc', blob.slice(1, 3).toString());
  assertEquals('def', blob.slice(3, 10).toString());
  assertEquals('abcd', blob.slice(0, -2).toString());
  assertEquals('', blob.slice(10, 1).toString());
  assertEquals('', blob.slice(10, 30).toString());
  assertEquals('b', blob.slice(-5, 2).toString());

  assertEquals('abcdef', blob.slice().toString());
  assertEquals('abc', blob.slice(/* opt_start */ undefined, 3).toString());
  assertEquals('def', blob.slice(3).toString());

  assertEquals('text/plain', blob.slice(1, 2, 'text/plain').type);

  blob = new goog.testing.fs.Blob('ab資cd');
  assertEquals('ab資', blob.slice(0, 5).toString());  // 資 is 3-bytes long.
  assertEquals('資', blob.slice(2, 5).toString());
  assertEquals('資cd', blob.slice(2, 10).toString());
  assertEquals('ab', blob.slice(0, -5).toString());
  assertEquals('c', blob.slice(-2, -1).toString());
  assertEquals('資c', blob.slice(-5, -1).toString());

  assertEquals('ab資cd', blob.slice().toString());
  assertEquals('ab資', blob.slice(/* opt_start */ undefined, 5).toString());
  assertEquals('cd', blob.slice(5).toString());
  assertArrayEquals([232], blob.slice(2, 3).data_);  // first byte of 資.
}

function testToArrayBuffer() {
  if (!hasArrayBuffer) {
    return;
  }
  var blob = new goog.testing.fs.Blob('資');
  var buf = new ArrayBuffer(this.size);
  var arr = new Uint8Array(buf);
  arr = [232, 179, 135];
  assertElementsEquals(buf, blob.toArrayBuffer());
}

function testToDataUrl() {
  var blob = new goog.testing.fs.Blob('資', 'text');
  assertEquals('data:text;base64,6LOH', blob.toDataUrl());
}
