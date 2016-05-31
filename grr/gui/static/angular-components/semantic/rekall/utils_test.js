'use strict';

goog.require('grrUi.semantic.rekall.utils.cropRekallJson');
goog.require('grrUi.semantic.rekall.utils.stackRekallTables');

goog.scope(function() {

describe('semantic.rekall.utils.cropRekallJson', function() {

  it('crops Rekall Json messages.', function() {
    //                                              50th byte mark: v
    var jsonStr = '[["L",{"msg":"foo"}],["L",{"msg":"bar"}],["m",{"se' +
                  'ssion":{}}]]';
    var targetLen = 50;

    var croppedJsonStr = grrUi.semantic.rekall.utils.cropRekallJson(
        jsonStr, targetLen);

    expect(croppedJsonStr).toBe('[["L",{"msg":"foo"}],["L",{"msg":"bar"}]]');
  });

  it('ignores brackets inside strings.', function() {
    //                                              50th byte mark: v
    var jsonStr = '[["L",{"msg":"]]]]]]]]][[][][]["}],["L",{"msg":"ba' +
                  'r"}],["m",{"session":{}}]]';
    var targetLen = 50;

    var croppedJsonStr = grrUi.semantic.rekall.utils.cropRekallJson(
        jsonStr, targetLen);

    expect(croppedJsonStr).toBe('[["L",{"msg":"]]]]]]]]][[][][]["}]]');
  });

  it('ignores escaped "s and \\s inside strings.', function() {
    // Note that escaped chars expansion is twofold here: JS and JSON both do
    // it. Therefore, var jsonStr = '["\\\\"]' would be a JSON-encoded list
    // containing a string containing a single backslash.

    var jsonStr = //                                   50th byte mark: v
        '[["L",{"msg":"]]\\"]\\"\\"\\"]]\\\\\\\\\\"]]]\\\\\\\\"}],["L",{' +
        '"msg":"bar"}],["m",{"session":{}}]]';

    var targetLen = 50;

    var croppedJsonStr = grrUi.semantic.rekall.utils.cropRekallJson(
        jsonStr, targetLen);

    expect(croppedJsonStr).toBe(
        '[["L",{"msg":"]]\\"]\\"\\"\\"]]\\\\\\\\\\"]]]\\\\\\\\"}]]');
  });

});

describe('semantic.rekall.utils.stackRekallTables', function() {

  it('Stacks rekall tables correctly.', function() {
    var parsedMessages = [['r', {'ip': '::1'}],
                          ['t', [{'cname': 'ip','name': 'IP Address'}]],
                          ['r', {'ip': '::2'}],
                          ['r', {'ip': '::3'}],
                          ['r', {'ip': '::4'}]];

    var stackedMessages = grrUi.semantic.rekall.utils.stackRekallTables(
        parsedMessages);

    expect(stackedMessages).toEqual([
        ['t', {'header': undefined,
               'rows': [{'ip': '::1'}]}],
        ['t', {'header': [{'cname': 'ip','name': 'IP Address'}],
               'rows': [{'ip': '::2'}, {'ip': '::3'}, {'ip': '::4'}]}]]);
  });

});

});  // goog.scope
