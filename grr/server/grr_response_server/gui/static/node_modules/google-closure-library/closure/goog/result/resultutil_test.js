// Copyright 2012 The Closure Library Authors. All Rights Reserved.
// Use of this source code is governed by the Apache License, Version 2.0.

goog.provide('goog.resultTest');
goog.setTestOnly('goog.resultTest');

goog.require('goog.result');
goog.require('goog.testing.jsunit');

function testSuccessfulResult() {
  var value = 'some-value';
  var result = goog.result.successfulResult(value);
  assertEquals(goog.result.Result.State.SUCCESS, result.getState());
  assertEquals(value, result.getValue());
}


function testFailedResult() {
  var error = new Error('something-failed');
  var result = goog.result.failedResult(error);
  assertEquals(goog.result.Result.State.ERROR, result.getState());
  assertEquals(error, result.getError());
}


function testCanceledResult() {
  var result = goog.result.canceledResult();
  assertEquals(goog.result.Result.State.ERROR, result.getState());

  var error = result.getError();
  assertTrue(error instanceof goog.result.Result.CancelError);
}
