'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('dict form directive', function() {
  var $compile, $rootScope, $q, grrReflectionService, value;

  beforeEach(module('/static/angular-components/forms/dict-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrFormValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    grrReflectionService.getRDFValueDescriptor = function(valueType) {
      if (valueType != 'RDFString') {
        throw new Error('This stub accepts only RDFString value type.');
      }

      var deferred = $q.defer();
      deferred.resolve({
        name: 'RDFString',
        default: {
          type: 'RDFString',
          value: ''
        }
      });
      return deferred.promise;
    };
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-form-dict value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('add empty key and value when "+" button is clicked', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');
    $rootScope.$apply();

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: ''}}
    });
  });

  it('updates the model when key is changed', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');
    $rootScope.$apply();

    element.find('input.key').val('foo');
    browserTrigger(element.find('input.key'), 'change');

    $rootScope.$apply();

    expect(model).toEqual({
      type: 'Dict',
      value: {'foo': {type: 'RDFString', value: ''}}
    });
  });

  it('updates the model when value is changed', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');
    $rootScope.$apply();

    var valueElement = element.find('grr-form-value');
    valueElement.scope().$eval(valueElement.attr('value') + '.value = "foo"');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: 'foo'}}
    });
  });

  it('prefills the UI with values from model', function() {
    var model = {
      type: 'Dict',
      value: {'foo': {type: 'RDFString', value: 'bar'}}
    };

    var element = renderTestTemplate(model);
    expect(element.find('input.key').val()).toBe('foo');

    var valueElement = element.find('grr-form-value');
    expect(valueElement.scope().$eval(valueElement.attr('value'))).toEqual(
        {type: 'RDFString', value: 'bar'});
  });

});
