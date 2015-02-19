'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('mac address directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-mac-address value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "-" when value is empty', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('-');
  });

  it('shows string value', function() {
    var element = renderTestTemplate('+BZUBnli');
    expect(element.text()).toContain('f8:16:54:06:79:62');
  });

  it('shows value with type information', function() {
    var macAddress = {
      age: 0,
      mro: ['MacAddress', 'RDFBytes', 'RDFValue', 'object'],
      type: 'MacAddress',
      value: '+BZUBnli'
    };
    var element = renderTestTemplate(macAddress);
    expect(element.text()).toContain('f8:16:54:06:79:62');
  });

});
