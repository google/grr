'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('dict semantic directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/semantic/dict.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-dict value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows empty table when value is empty', function() {
    var element = renderTestTemplate({
      type: 'dict',
      value: {
      }
    });
    expect(element.find('table').length).toBe(1);
    expect(element.find('tr').length).toBe(0);
  });

  it('shows 2 keys and corresponding values for value with 2 keys', function() {
    var element = renderTestTemplate({
      type: 'dict',
      value: {
        fooKey: {type: 'Foo'},
        barKey: {type: 'Bar'}
      }
    });
    expect(element.find('table').length).toBe(1);
    expect(element.find('tr').length).toBe(2);

    expect(element.text()).toContain('fooKey');
    expect(element.text()).toContain('barKey');

    expect(element.find('grr-semantic-value').length).toBe(2);
  });

});
