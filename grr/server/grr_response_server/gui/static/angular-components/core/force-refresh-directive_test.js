'use strict';

goog.module('grrUi.core.forceRefreshDirectiveTest');

const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-force-refresh directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    $rootScope.value = 42;
  }));

  const render = (objectEquality) => {
    $rootScope.objectEquality = objectEquality;

    const template = '<grr-force-refresh object-equality="objectEquality" ' +
        'refresh-trigger="value">' +
        '{$ ::value $}</grr-force-refresh>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows transcluded template immediately', () => {
    const element = render();
    expect(element.text()).toContain('42');
  });

  it('reloads children elements effectively updating one-time bindings', () => {
    const element = render();
    expect(element.text()).toContain('42');

    $rootScope.value = 43;
    $rootScope.$apply();
    expect(element.text()).toContain('43');
  });

  it('reloads on object-level changes', () => {
    $rootScope.value = {
      a: 'a',
    };
    const element = render(true);
    expect(element.text()).toContain('{"a":"a"}');

    $rootScope.value['a'] = 'b';
    $rootScope.$apply();
    expect(element.text()).toContain('{"a":"b"}');
  });
});


exports = {};
