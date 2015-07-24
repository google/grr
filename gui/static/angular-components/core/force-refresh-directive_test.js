'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

describe('grr-force-refresh directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  it('reloads children elements effectively updating one-time bindings',
     function() {
    $rootScope.value = 42;

    var template = '<div grr-force-refresh refresh-trigger="value">' +
        '{$ ::value $}</div>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    expect(element.text()).toContain('42');

    $rootScope.value = 43;
    $rootScope.$apply();
    expect(element.text()).toContain('43');
  });

});
