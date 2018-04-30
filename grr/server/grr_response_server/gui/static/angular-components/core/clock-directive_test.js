'use strict';

goog.module('grrUi.core.clockDirectiveTest');

const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('clock directive', () => {
  let $compile;
  let $interval;
  let $rootScope;
  let grrTimeService;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector, _$interval_) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = _$interval_;
    grrTimeService = $injector.get('grrTimeService');
  }));

  afterEach(inject(($injector) => {
    grrTimeService = $injector.get('grrTimeService');
  }));

  const renderTestTemplate = () => {
    const template = '<grr-live-clock />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows the current time in a clock', () => {
    let time = '2015-01-02 03:04:05';

    grrTimeService.formatAsUTC = (() => `${time} UTC`);

    const newElement = renderTestTemplate();

    // Live clock must use UTC time and label it.
    expect(newElement.text()).toContain('2015-01-02 03:04:05 UTC');

    // Make sure time changes are effected in the live clock.
    time = '2015-01-02 03:04:06';

    $interval.flush(60000);

    expect(newElement.text()).toContain('03:04:06');
  });
});


exports = {};
