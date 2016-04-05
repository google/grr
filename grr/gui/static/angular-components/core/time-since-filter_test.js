'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.core.timeSinceFilter.TimeSinceFilter');
goog.require('grrUi.tests.module');

describe('grrTimeSince filter', function() {
  var grrTimeSinceFilter;
  var referenceTime = 5 * 60 * 60 * 24 * 1000000;

  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    grrTimeSinceFilter = $injector.instantiate(
        grrUi.core.timeSinceFilter.TimeSinceFilter,
        {
          'grrTimeService': {
            'getCurrentTimeMs': function() { return referenceTime / 1000; }
          }
        });
  }));

  it('returns seconds when value is 42 seconds ago', function() {
    var result = grrTimeSinceFilter(referenceTime - 42 * 1000000);
    expect(result).toBe('42 seconds ago');
  });

  it('returns hours when value is 3 hours ago', function() {
    var result = grrTimeSinceFilter(referenceTime -
        (60 * 60 * 3 + 42) * 1000000);
    expect(result).toBe('3 hours ago');
  });

  it('returns days when value is 3 days ago', function() {
    var result = grrTimeSinceFilter(referenceTime -
        (60 * 60 * 24 * 3 + 42) * 1000000);
    expect(result).toBe('3 days ago');
  });

  it('returns seconds when value is 42 seconds in the future', function() {
    var result = grrTimeSinceFilter(referenceTime + 42 * 1000000);
    expect(result).toBe('in 42 seconds');
  });

  it('returns hours when value is 3 hours in the future', function() {
    var result = grrTimeSinceFilter(referenceTime +
        (60 * 60 * 3 + 42) * 1000000);
    expect(result).toBe('in 3 hours');
  });

  it('returns days when value is 3 days in the future', function() {
    var result = grrTimeSinceFilter(referenceTime +
        (60 * 60 * 24 * 3 + 42) * 1000000);
    expect(result).toBe('in 3 days');
  });

  it('returns error message when value is 0', function() {
    var result = grrTimeSinceFilter(0);
    expect(result).toBe('<invalid time value>');
  });
});
