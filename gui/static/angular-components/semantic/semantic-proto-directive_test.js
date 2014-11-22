'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

goog.scope(function() {

describe('semantic proto directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/semantic/semantic-proto.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-semantic-proto value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is empty', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('');
  });

  it('respects fields order', function() {
    var element = renderTestTemplate({
      fields_order: ['client_id', 'system_info', 'client_info'],
      value: {
        client_id: 'client_id',
        system_info: 'system_info',
        client_info: 'client_info'
      }
    });
    expect($('tr:nth(0)', element).text()).toContain('client_id');
    expect($('tr:nth(1)', element).text()).toContain('system_info');
    expect($('tr:nth(2)', element).text()).toContain('client_info');

    element = renderTestTemplate({
      fields_order: ['client_info', 'system_info', 'client_id'],
      value: {
        client_id: 'client_id',
        system_info: 'system_info',
        client_info: 'client_info'
      }
    });
    expect($('tr:nth(0)', element).text()).toContain('client_info');
    expect($('tr:nth(1)', element).text()).toContain('system_info');
    expect($('tr:nth(2)', element).text()).toContain('client_id');
  });

  it('renders nested RDFProtoStruct', function() {
    var element = renderTestTemplate({
      fields_order: ['field', 'nested'],
      value: {
        field: 'foobar',
        nested: {
          mro: ['RDFProtoStruct'],
          fields_order: ['nested_field1', 'nested_field2'],
          value: {
            nested_field1: 42,
            nested_field2: 'nested_field_value'
          }
        }
      }
    });

    expect($('tr:nth(0)', element).text()).toContain('field');
    expect($('tr:nth(0)', element).text()).toContain('foobar');

    expect($('tr:nth(1) tr:nth(0)', element).text()).toContain('nested_field1');
    expect($('tr:nth(1) tr:nth(0)', element).text()).toContain('42');

    expect($('tr:nth(1) tr:nth(1)', element).text()).toContain('nested_field2');
    expect($('tr:nth(1) tr:nth(1)', element).text()).toContain(
        'nested_field_value');
  });

});

});  // goog.scope
