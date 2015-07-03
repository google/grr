'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('semantic primitive form directive', function() {
  var $compile, $rootScope, $q, grrReflectionService;
  var stringValue, intValue, boolValue;

  beforeEach(module('/static/angular-components/forms/semantic-primitive-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    grrReflectionService.getRDFValueDescriptor = function(valueType) {
      var deferred = $q.defer();
      deferred.resolve({
        name: valueType,
        mro: [valueType]
      });
      return deferred.promise;
    };

    stringValue = {
      type: 'RDFString',
      value: 'foo'
    };

    intValue = {
      type: 'RDFInteger',
      value: 42
    };

    boolValue = {
      type: 'RDFBool',
      value: true
    };
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-form-primitive value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('prefills RDFString value from a model', function() {
    var element = renderTestTemplate(stringValue);
    expect(element.find('input').val()).toBe('foo');
  });

  it('updates RDFString value when model is updated', function() {
    var element = renderTestTemplate(stringValue);
    expect(element.find('input').val()).toBe('foo');

    stringValue.value = 'bar';
    $rootScope.$apply();

    expect(element.find('input').val()).toBe('bar');
  });

  it('updates RDFString model when user changes the input', function() {
    var element = renderTestTemplate(stringValue);

    element.find('input').val('bar');
    browserTrigger(element.find('input'), 'change');
    $rootScope.$apply();

    expect(stringValue.value).toBe('bar');
  });

  it('prefills RDFInteger value from a model', function() {
    var element = renderTestTemplate(intValue);
    expect(element.find('input').val()).toBe('42');
  });

  it('updates RDFInteger value when model is updated', function() {
    var element = renderTestTemplate(intValue);
    expect(element.find('input').val()).toBe('42');

    intValue.value = 84;
    $rootScope.$apply();

    expect(element.find('input').val()).toBe('84');
  });

  it('updates RDFInteger model when user changes the input', function() {
    var element = renderTestTemplate(intValue);

    element.find('input').val('84');
    browserTrigger(element.find('input'), 'change');
    $rootScope.$apply();

    expect(intValue.value).toBe(84);
  });

  it('prefills RDFBool value from a model', function() {
    var element = renderTestTemplate(boolValue);
    expect(element.find('input').prop('checked')).toBe(true);
  });

  it('updates RDFBool value when model is updated', function() {
    var element = renderTestTemplate(boolValue);
    expect(element.find('input').prop('checked')).toBe(true);

    boolValue.value = false;
    $rootScope.$apply();

    expect(element.find('input').prop('checked')).toBe(false);
  });

  it('updates RDFBool model when user changes the input', function() {
    var element = renderTestTemplate(boolValue);

    browserTrigger(element.find('input'), 'click');
    $rootScope.$apply();

    expect(boolValue.value).toBe(false);
  });

});
