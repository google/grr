'use strict';

goog.module('grrUi.core.canaryOnlyDirectiveTest');

const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('The canaryOnlyDirective package', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = () => {
    const template = '<grr-canary-only>' +
        'This text is being canaried.' +
        '</grr-canary-only>' +
        '<grr-non-canary-only>' +
        'This text is being deprecated.' +
        '</grr-non-canary-only>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const setMockedCanaryModeValue = (newValue) => {
    const deferred = $q.defer();
    deferred.resolve(
        {data: {value: {settings: {value: {canary_mode: {value: newValue}}}}}});
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);
  };

  it('renders the grr-canary-only element in canary mode', () => {
    setMockedCanaryModeValue(true);
    const element = renderTestTemplate();
    expect(element.text()).toContain('This text is being canaried.');
  });

  it('doesn\'t render the grr-canary-only element in non-canary mode', () => {
    setMockedCanaryModeValue(false);
    const element = renderTestTemplate();
    expect(element.text()).not.toContain('This text is being canaried.');
  });

  it('renders the grr-non-canary-only element in non-canary mode', () => {
    setMockedCanaryModeValue(false);
    const element = renderTestTemplate();
    expect(element.text()).toContain('This text is being deprecated.');
  });

  it('doesn\'t render the grr-non-canary-only element in canary mode', () => {
    setMockedCanaryModeValue(true);
    const element = renderTestTemplate();
    expect(element.text()).not.toContain('This text is being deprecated.');
  });
});


exports = {};
