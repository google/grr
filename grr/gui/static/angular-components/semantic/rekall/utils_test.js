'use strict';

goog.module('grrUi.semantic.rekall.utilsTest');

const {cropRekallJson, stackRekallTables} = goog.require('grrUi.semantic.rekall.utils');


describe('semantic.rekall.utils.cropRekallJson', () => {
  it('crops Rekall Json messages.', () => {
    //                                              50th byte mark: v
    const jsonStr = '[["L",{"msg":"foo"}],["L",{"msg":"bar"}],["m",{"se' +
        'ssion":{}}]]';
    const targetLen = 50;

    const croppedJsonStr = cropRekallJson(jsonStr, targetLen);

    expect(croppedJsonStr).toBe('[["L",{"msg":"foo"}],["L",{"msg":"bar"}]]');
  });

  it('ignores brackets inside strings.', () => {
    //                                              50th byte mark: v
    const jsonStr = '[["L",{"msg":"]]]]]]]]][[][][]["}],["L",{"msg":"ba' +
        'r"}],["m",{"session":{}}]]';
    const targetLen = 50;

    const croppedJsonStr = cropRekallJson(jsonStr, targetLen);

    expect(croppedJsonStr).toBe('[["L",{"msg":"]]]]]]]]][[][][]["}]]');
  });

  it('ignores escaped "s and \\s inside strings.', () => {
    // Note that escaped chars expansion is twofold here: JS and JSON both do
    // it. Therefore, var jsonStr = '["\\\\"]' would be a JSON-encoded list
    // containing a string containing a single backslash.

    const jsonStr =  //                                   50th byte mark: v
        '[["L",{"msg":"]]\\"]\\"\\"\\"]]\\\\\\\\\\"]]]\\\\\\\\"}],["L",{' +
        '"msg":"bar"}],["m",{"session":{}}]]';

    const targetLen = 50;

    const croppedJsonStr = cropRekallJson(jsonStr, targetLen);

    expect(croppedJsonStr).toBe(
        '[["L",{"msg":"]]\\"]\\"\\"\\"]]\\\\\\\\\\"]]]\\\\\\\\"}]]');
  });
});

describe('semantic.rekall.utils.stackRekallTables', () => {
  it('Stacks rekall tables correctly.', () => {
    const parsedMessages = [
      ['r', {'ip': '::1'}], ['t', [{'cname': 'ip', 'name': 'IP Address'}]],
      ['r', {'ip': '::2'}], ['r', {'ip': '::3'}], ['r', {'ip': '::4'}]
    ];

    const stackedMessages = stackRekallTables(parsedMessages);

    expect(stackedMessages).toEqual([
        ['t', {'header': undefined,
               'rows': [{'ip': '::1'}]}],
        ['t', {'header': [{'cname': 'ip','name': 'IP Address'}],
               'rows': [{'ip': '::2'}, {'ip': '::3'}, {'ip': '::4'}]}]]);
  });
});


exports = {};
