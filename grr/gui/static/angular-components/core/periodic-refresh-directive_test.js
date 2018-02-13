'use strict';

goog.module('grrUi.core.periodicRefreshDirectiveTest');

const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-periodic-refresh directive', () => {
  let $compile;
  let $interval;
  let $rootScope;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $interval = $injector.get('$interval');
    $rootScope = $injector.get('$rootScope');
  }));

  it('reloads children elements effectively updating one-time bindings', () => {
    $rootScope.value = 42;

    const template = '<grr-periodic-refresh interval="1000">' +
        '{$ ::value $}</grr-periodic-refresh>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    expect(element.text()).toContain('42');

    $rootScope.value = 43;
    $rootScope.$apply();

    // The value was updated but DOM stays the same, as one-time binding
    // is used in the template.
    expect(element.text()).toContain('42');

    // Transcluded template gets re-rendered when the timer hits.
    $interval.flush(1001);
    expect(element.text()).toContain('43');
  });

  it('calls a callback on timer', () => {
    $rootScope.callback = jasmine.createSpy('callback');

    const template = '<grr-periodic-refresh interval="1000" ' +
        'on-refresh="callback()"></grr-periodic-refresh>';
    $compile(template)($rootScope);
    $rootScope.$apply();

    expect($rootScope.callback).not.toHaveBeenCalled();

    $interval.flush(1001);
    expect($rootScope.callback).toHaveBeenCalled();
  });
});


exports = {};
