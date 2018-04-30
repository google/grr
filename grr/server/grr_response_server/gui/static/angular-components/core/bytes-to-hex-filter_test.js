'use strict';

goog.module('grrUi.core.bytesToHexFilterTest');

const {BytesToHexFilter} = goog.require('grrUi.core.bytesToHexFilter');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('grrBytesToHex filter', () => {
  let grrBytesToHexFilter;

  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    grrBytesToHexFilter = $injector.instantiate(BytesToHexFilter);
  }));

  it('returns the correct hex for different input bytes', () => {
    let result = grrBytesToHexFilter('some text');
    expect(result).toBe('736f6d652074657874');

    result = grrBytesToHexFilter('123abc');
    expect(result).toBe('313233616263');
  });
});


exports = {};
