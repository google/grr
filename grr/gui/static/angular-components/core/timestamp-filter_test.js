'use strict';

goog.module('grrUi.core.timestampFilterTest');

const {TimestampFilter} = goog.require('grrUi.core.timestampFilter');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('grrTimestamp filter', () => {
  const MICRO_IN_MILLI = 1000;
  const MILLI_IN_UNIT = 1000;

  const SECONDS = MICRO_IN_MILLI * MILLI_IN_UNIT;
  const MINUTES = 60 * SECONDS;
  let grrTimestampFilter;

  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    grrTimestampFilter = $injector.instantiate(TimestampFilter);
  }));

  it('returns reference date on 0', () => {
    const result = grrTimestampFilter(0);
    expect(result).toBe('1970-01-01 00:00:00 UTC');
  });

  it('returns correct value for seconds', () => {
    const result = grrTimestampFilter(42 * SECONDS);
    expect(result).toBe('1970-01-01 00:00:42 UTC');
  });

  it('returns correct value for minutes', () => {
    const result = grrTimestampFilter(10 * MINUTES + 42 * SECONDS);
    expect(result).toBe('1970-01-01 00:10:42 UTC');
  });
});


exports = {};
