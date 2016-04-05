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

  var setFormValue = function(element, value) {
    var valueElement = element.find('grr-form-value');
    valueElement.scope().$eval(valueElement.attr('value') + '.value = "' +
        value + '"');
    $rootScope.$apply();
  };

  it('add empty key and value when "+" button is clicked', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');

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

    element.find('input.key').val('foo');
    browserTrigger(element.find('input.key'), 'change');

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
    setFormValue(element, 'foo');

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

  it('treats digits-only string as integers', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');
    setFormValue(element, '42');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFInteger', value: 42}}
    });
  });

  it('dynamically changes value type from str to int and back', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: ''}}
    });

    setFormValue(element, '1');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFInteger', value: 1}}
    });

    setFormValue(element, '1a');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: '1a'}}
    });
  });

  it('treats 0x.* strings as hex integers', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');
    setFormValue(element, '0x2f');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFInteger', value: 47}}
    });
  });

  it('dynamically changes value type from hex int to str and back', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: ''}}
    });

    setFormValue(element, '0x');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: '0x'}}
    });

    setFormValue(element, '0x2f');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFInteger', value: 47}}
    });

    setFormValue(element, '0x2fz');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: '0x2fz'}}
    });
  });

  it('treats "true" string as a boolean', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');
    setFormValue(element, 'true');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFBool', value: true}}
    });
  });

  it('treats "false" string as a boolean', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');
    setFormValue(element, 'false');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFBool', value: false}}
    });
  });

  it('dynamically changes valye type from text to bool and back', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: ''}}
    });

    setFormValue(element, 'true');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFBool', value: true}}
    });

    setFormValue(element, 'truea');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: 'truea'}}
    });

  });
});
