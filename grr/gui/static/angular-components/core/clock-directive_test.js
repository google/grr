'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

describe('clock directive', function() {
  var MICRO_IN_MILLI = 1000, MILLI_IN_UNIT = 1000;
  var SECONDS = MICRO_IN_MILLI * MILLI_IN_UNIT;
  var MINUTES = 60 * SECONDS;
  var $compile, $rootScope, $interval,
      grrTimeService;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector, _$interval_) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = _$interval_;
    grrTimeService = $injector.get('grrTimeService');
  }));

  afterEach(inject(function($injector) {
    grrTimeService = $injector.get('grrTimeService');
  }));

  var renderTestTemplate = function() {
    var template = '<grr-live-clock />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows the current time in a clock', function() {
    var element = renderTestTemplate();
    var time = '2015-01-02 03:04:05';

    grrTimeService.formatAsUTC = function() {
      return time + ' UTC';
    };

    var newElement = renderTestTemplate();

    // Live clock must use UTC time and label it.
    expect(newElement.text()).toContain('2015-01-02 03:04:05 UTC');

    // Make sure time changes are effected in the live clock.
    time = '2015-01-02 03:04:06';

    $interval.flush(60000);

    expect(newElement.text()).toContain('03:04:06');
  });
});
