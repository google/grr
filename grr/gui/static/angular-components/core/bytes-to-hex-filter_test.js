'use strict';

goog.require('grrUi.core.bytesToHexFilter.BytesToHexFilter');
goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

describe('grrBytesToHex filter', function() {
  var grrBytesToHexFilter;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    grrBytesToHexFilter = $injector.instantiate(
        grrUi.core.bytesToHexFilter.BytesToHexFilter);
  }));

  it('returns the correct hex for different input bytes', function() {
    var result = grrBytesToHexFilter('some text');
    expect(result).toBe('736f6d652074657874');

    result = grrBytesToHexFilter('123abc');
    expect(result).toBe('313233616263');
  });
});
