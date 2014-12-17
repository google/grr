'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('timestamp directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-timestamp value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is unedfined', function() {
    var element = renderTestTemplate(undefined);
    expect(element.text().trim()).toBe('');
  });

  it('does not show anything when value is null', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('-');
  });

  it('shows "-" when value is 0', function() {
    var element = renderTestTemplate(0);
    expect(element.text().trim()).toBe('-');
  });

  it('shows integer value', function() {
    var element = renderTestTemplate(42 * 1000000);
    expect(element.text()).toContain('1970-01-01 00:00:42');
  });

  it('shows value with type information', function() {
    var timestamp = {
      'mro': ['RDFDatetime', 'RDFInteger', 'RDFString', 'RDFBytes', 'RDFValue',
              'object'],
      'value': 42 * 1000000,
      'age': 0,
      'type': 'RDFDatetime'
    };
    var element = renderTestTemplate(timestamp);
    expect(element.text()).toContain('1970-01-01 00:00:42');
  });

});
