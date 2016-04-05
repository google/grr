'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.core.timestampFilter.TimestampFilter');
goog.require('grrUi.tests.module');

describe('grrTimestamp filter', function() {
  var MICRO_IN_MILLI = 1000, MILLI_IN_UNIT = 1000;
  var SECONDS = MICRO_IN_MILLI * MILLI_IN_UNIT;
  var MINUTES = 60 * SECONDS;
  var grrTimestampFilter;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    grrTimestampFilter = $injector.instantiate(
        grrUi.core.timestampFilter.TimestampFilter);
  }));

  it('returns reference date on 0', function() {
    var result = grrTimestampFilter(0);
    expect(result).toBe('1970-01-01 00:00:00 UTC');
  });

  it('returns correct value for seconds', function() {
    var result = grrTimestampFilter(42 * SECONDS);
    expect(result).toBe('1970-01-01 00:00:42 UTC');
  });

  it('returns correct value for minutes', function() {
    var result = grrTimestampFilter(10 * MINUTES + 42 * SECONDS);
    expect(result).toBe('1970-01-01 00:10:42 UTC');
  });

});
