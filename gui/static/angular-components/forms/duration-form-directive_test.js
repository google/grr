'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('duration form directive', function() {
  var $compile, $rootScope, value;

  beforeEach(module('/static/angular-components/forms/duration-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-form-duration value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if duration value is null', function() {
    var element = renderTestTemplate({
      type: 'Duration',
      value: null
    });
    expect(element.find('input').val()).toBe('');
  });

  it('shows 0 if duration value is 0', function() {
    var element = renderTestTemplate({
      type: 'Duration',
      value: 0
    });
    expect(element.find('input').val()).toBe('0');
  });

  it('shows correct duration for large numbers', function() {
    var element = renderTestTemplate({
      type: 'Duration',
      value: 1040688000000
    });
    expect(element.find('input').val()).toBe('12045000d');
  });

  it('shows duration in seconds if it\'s not divisible by 60', function() {
    var element = renderTestTemplate({
      type: 'Duration',
      value: 122
    });
    expect(element.find('input').val()).toBe('122s');
  });

  it('shows duration in minutes if possible', function() {
    var element = renderTestTemplate({
      type: 'Duration',
      value: 120
    });
    expect(element.find('input').val()).toBe('2m');
  });

  it('shows duration in hours if possible', function() {
    var element = renderTestTemplate({
      type: 'Duration',
      value: 7200
    });
    expect(element.find('input').val()).toBe('2h');
  });

  it('shows duration in days if possible', function() {
    var element = renderTestTemplate({
      type: 'Duration',
      value: 172800
    });
    expect(element.find('input').val()).toBe('2d');
  });

  it('shows duration in weeks if possible', function() {
    var element = renderTestTemplate({
      type: 'Duration',
      value: 1209600
    });
    expect(element.find('input').val()).toBe('2w');
  });

  it('sets value to null on incorrect input', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('a');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(null);
  });

  it('shows warning on incorrect input', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('a');
    browserTrigger(element.find('input'), 'change');

    expect(element.text()).toContain('Expected format is');
  });

  it('correctly updates the value when input is in weeks', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('2w');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(1209600);
  });

  it('correctly updates the value when input is in days', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('2d');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(172800);
  });

  it('correctly updates the value when input is in hours', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('2h');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(7200);
  });

  it('correctly updates the value when input is in minutes', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('2m');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(120);
  });

  it('correctly updates the value when input is in seconds', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('2s');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(2);
  });

  it('treats values without unit as seconds', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('2');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(2);
  });
});
