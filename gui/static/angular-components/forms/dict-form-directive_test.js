'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('dict form directive', function() {
  var $compile, $rootScope, value;

  beforeEach(module('/static/angular-components/forms/dict-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
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
      value: {'': ''}
    });
  });

  it('updates the model when key and value inputs are changed', function() {
    var model = {
      type: 'Dict',
      value: {}
    };
    var element = renderTestTemplate(model);

    browserTrigger(element.find('button[name=Add]'), 'click');
    $rootScope.$apply();

    element.find('input.key').val('foo');
    browserTrigger(element.find('input.key'), 'change');

    element.find('input.value').val('bar');
    browserTrigger(element.find('input.value'), 'change');

    $rootScope.$apply();

    expect(model).toEqual({
      type: 'Dict',
      value: {'foo': 'bar'}
    });
  });

  it('prefills the UI with values from model', function() {
    var model = {
      type: 'Dict',
      value: {'foo': 'bar'}
    };
    var element = renderTestTemplate(model);

    expect(element.find('input.key').val()).toBe('foo');
    expect(element.find('input.value').val()).toBe('bar');
  });

});
