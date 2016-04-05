'use strict';

goog.require('grrUi.core.hexNumberFilter.HexNumberFilter');
goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

describe('grrHexNumber filter', function() {
  var grrHexNumberFilter;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    grrHexNumberFilter = $injector.instantiate(
        grrUi.core.hexNumberFilter.HexNumberFilter);
  }));

  it('returns the correct hex for different input numbers', function() {
    var result = grrHexNumberFilter(0);
    expect(result).toBe('0x00000000');

    result = grrHexNumberFilter(255);
    expect(result).toBe('0x000000ff');

    result = grrHexNumberFilter(1010101);
    expect(result).toBe('0x000f69b5');

    result = grrHexNumberFilter(4294967296 - 1);
    expect(result).toBe('0xffffffff');
  });

  it('inserts leading 0s to always return a multiple of eight places', function() {
    var result = grrHexNumberFilter(1);
    expect(result).toBe('0x00000001');

    result = grrHexNumberFilter(4294967296);
    expect(result).toBe('0x0000000100000000');
  });
});
