'use strict';

goog.module('grrUi.core.hexNumberFilterTest');

const {HexNumberFilter} = goog.require('grrUi.core.hexNumberFilter');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('grrHexNumber filter', () => {
  let grrHexNumberFilter;

  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    grrHexNumberFilter = $injector.instantiate(HexNumberFilter);
  }));

  it('returns the correct hex for different input numbers', () => {
    let result = grrHexNumberFilter(0);
    expect(result).toBe('0x00000000');

    result = grrHexNumberFilter(255);
    expect(result).toBe('0x000000ff');

    result = grrHexNumberFilter(1010101);
    expect(result).toBe('0x000f69b5');

    result = grrHexNumberFilter(4294967296 - 1);
    expect(result).toBe('0xffffffff');
  });

  it('inserts leading 0s to always return a multiple of eight places', () => {
    let result = grrHexNumberFilter(1);
    expect(result).toBe('0x00000001');

    result = grrHexNumberFilter(4294967296);
    expect(result).toBe('0x0000000100000000');
  });
});


exports = {};
