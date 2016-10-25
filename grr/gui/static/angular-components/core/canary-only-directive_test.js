'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');


describe('The canaryOnlyDirective package', function() {
  var $compile, $rootScope, $q, grrApiService;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function() {
    var template = '<grr-canary-only>' +
                     'This text is being canaried.' +
                   '</grr-canary-only>' +
                   '<grr-non-canary-only>' +
                     'This text is being deprecated.' +
                   '</grr-non-canary-only>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  var setMockedCanaryModeValue = function(newValue) {
    var deferred = $q.defer();
    deferred.resolve(
        {data: {value: {settings: {value: {canary_mode: {value: newValue}}}}}});
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);
  };

  it('renders the grr-canary-only element in canary mode', function() {
    setMockedCanaryModeValue(true);
    var element = renderTestTemplate();
    expect(element.text()).toContain('This text is being canaried.');
  });

  it('doesn\'t render the grr-canary-only element in non-canary mode',
      function() {
    setMockedCanaryModeValue(false);
    var element = renderTestTemplate();
    expect(element.text()).not.toContain('This text is being canaried.');
  });

  it('renders the grr-non-canary-only element in non-canary mode', function() {
    setMockedCanaryModeValue(false);
    var element = renderTestTemplate();
    expect(element.text()).toContain('This text is being deprecated.');
  });

  it('doesn\'t render the grr-non-canary-only element in canary mode',
      function() {
    setMockedCanaryModeValue(true);
    var element = renderTestTemplate();
    expect(element.text()).not.toContain('This text is being deprecated.');
  });

});
