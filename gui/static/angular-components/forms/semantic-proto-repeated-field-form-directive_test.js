'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('semantic proto repeated field form directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/forms/semantic-proto-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-union-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-single-field-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-repeated-field-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value, descriptor, field) {
    $rootScope.value = value;
    $rootScope.descriptor = descriptor;
    $rootScope.field = field;

    var template = '<grr-form-proto-repeated-field value="value" ' +
        'descriptor="descriptor" field="field" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  var typedPrimitiveValue = {
    type: 'PrimitiveType',
    mro: ['PrimitiveType'],
    value: 42
  };

  it('renders doc and friendly name', function() {
    var element = renderTestTemplate([], {}, {
      doc: 'Field documentation',
      friendly_name: 'Field friendly name'
    });

    expect(element.find('label[title="Field documentation"]').length).toBe(1);
    expect(element.text()).toContain('Field friendly name');
  });

  it('delegates items rendering to grr-form-value', function() {
    var element = renderTestTemplate(
        [{type: 'Foo', mro: ['Foo'], value: 42},
         {type: 'Foo', mro: ['Foo'], value: 43}], {}, {});

    expect(element.find('grr-form-value').length).toBe(2);
  });

  it('adds new item when "Add" is clicked', function() {
    var value = [];
    var descriptor = {
      default: angular.copy(typedPrimitiveValue)
    };

    var element = renderTestTemplate(value, descriptor, {});
    expect(element.find('grr-form-value').length).toBe(0);

    browserTrigger($('button[name=Add]', element), 'click');
    expect(element.find('grr-form-value').length).toBe(1);
    // Please see http://stackoverflow.com/a/26370331 on why we're using here
    // angular.equals() and not Jasmine's toEqual here.
    expect(angular.equals(value, [typedPrimitiveValue])).toBe(true);

    browserTrigger($('button[name=Add]', element), 'click');
    expect(element.find('grr-form-value').length).toBe(2);
    expect(angular.equals(value, [typedPrimitiveValue,
                                  typedPrimitiveValue])).toBe(true);
  });

  it('removes an item when "Remove" is clicked', function() {
    var value = [angular.copy(typedPrimitiveValue),
                 angular.copy(typedPrimitiveValue)];

    var element = renderTestTemplate(value, {}, {});
    expect(element.find('grr-form-value').length).toBe(2);

    browserTrigger($('button[name=Remove]:nth(0)', element), 'click');
    expect(element.find('grr-form-value').length).toBe(1);
    expect(angular.equals(value, [typedPrimitiveValue])).toBe(true);

    browserTrigger($('button[name=Remove]:nth(0)', element), 'click');
    expect(element.find('grr-form-value').length).toBe(0);
    expect(value).toEqual([]);
  });
});
