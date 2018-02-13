'use strict';

goog.module('grrUi.core.timeSinceFilterTest');

const {TimeSinceFilter} = goog.require('grrUi.core.timeSinceFilter');
const {clientModule} = goog.require('grrUi.client.client');
const {testsModule} = goog.require('grrUi.tests');


describe('grrTimeSince filter', () => {
  let grrTimeSinceFilter;
  const referenceTime = 5 * 60 * 60 * 24 * 1000000;

  beforeEach(module(clientModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    grrTimeSinceFilter = $injector.instantiate(TimeSinceFilter, {
      'grrTimeService': {
        'getCurrentTimeMs': function() {
          return referenceTime / 1000;
        },
      },
    });
  }));

  it('returns seconds when value is 42 seconds ago', () => {
    const result = grrTimeSinceFilter(referenceTime - 42 * 1000000);
    expect(result).toBe('42 seconds ago');
  });

  it('returns hours when value is 3 hours ago', () => {
    const result =
        grrTimeSinceFilter(referenceTime - (60 * 60 * 3 + 42) * 1000000);
    expect(result).toBe('3 hours ago');
  });

  it('returns days when value is 3 days ago', () => {
    const result =
        grrTimeSinceFilter(referenceTime - (60 * 60 * 24 * 3 + 42) * 1000000);
    expect(result).toBe('3 days ago');
  });

  it('returns seconds when value is 42 seconds in the future', () => {
    const result = grrTimeSinceFilter(referenceTime + 42 * 1000000);
    expect(result).toBe('in 42 seconds');
  });

  it('returns hours when value is 3 hours in the future', () => {
    const result =
        grrTimeSinceFilter(referenceTime + (60 * 60 * 3 + 42) * 1000000);
    expect(result).toBe('in 3 hours');
  });

  it('returns days when value is 3 days in the future', () => {
    const result =
        grrTimeSinceFilter(referenceTime + (60 * 60 * 24 * 3 + 42) * 1000000);
    expect(result).toBe('in 3 days');
  });

  it('returns error message when value is 0', () => {
    const result = grrTimeSinceFilter(0);
    expect(result).toBe('<invalid time value>');
  });
});


exports = {};
