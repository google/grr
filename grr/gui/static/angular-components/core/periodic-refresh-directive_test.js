'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

describe('grr-periodic-refresh directive', function() {
  var $compile, $interval, $rootScope;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $interval = $injector.get('$interval');
    $rootScope = $injector.get('$rootScope');
  }));

  it('reloads children elements effectively updating one-time bindings',
     function() {
    $rootScope.value = 42;

    var template = '<grr-periodic-refresh interval="1000">' +
        '{$ ::value $}</grr-periodic-refresh>';
    var element = $compile(template)($rootScope);
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

  it('calls a callback on timer', function() {
    $rootScope.callback = jasmine.createSpy('callback');

    var template = '<grr-periodic-refresh interval="1000" ' +
        'on-refresh="callback()"></grr-periodic-refresh>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    expect($rootScope.callback).not.toHaveBeenCalled();

    $interval.flush(1001);
    expect($rootScope.callback).toHaveBeenCalled();
  });

});
