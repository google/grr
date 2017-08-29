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

    $rootScope.value = 42;
  }));

  var render = function(objectEquality) {
    $rootScope.objectEquality = objectEquality;

    var template = '<grr-force-refresh object-equality="objectEquality" ' +
        'refresh-trigger="value">' +
        '{$ ::value $}</grr-force-refresh>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows transcluded template immediately', function() {
    var element = render();
    expect(element.text()).toContain('42');
  });

  it('reloads children elements effectively updating one-time bindings',
     function() {
    var element = render();
    expect(element.text()).toContain('42');

    $rootScope.value = 43;
    $rootScope.$apply();
    expect(element.text()).toContain('43');
  });

  it('reloads on object-level changes', function() {
    $rootScope.value = {
      a: 'a'
    };
    var element = render(true);
    expect(element.text()).toContain('{"a":"a"}');

    $rootScope.value['a'] = 'b';
    $rootScope.$apply();
    expect(element.text()).toContain('{"a":"b"}');
  });

});
