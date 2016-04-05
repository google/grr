'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('duration directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-duration value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "-" when value is empty', function() {
    var value = {
      type: 'Duration',
      value: null
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('-');
  });

  it('shows 0 if duration value is 0', function() {
    var value = {
      type: 'Duration',
      value: 0
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('0');
  });

  it('shows duration in seconds if it\'s not divisible by 60', function() {
    var value = {
      type: 'Duration',
      value: 122
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('122s');
  });

  it('shows duration in minutes if possible', function() {
    var value = {
      type: 'Duration',
      value: 120
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('2m');
  });

  it('shows duration in hours if possible', function() {
    var value = {
      type: 'Duration',
      value: 7200
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('2h');
  });

  it('shows duration in days if possible', function() {
    var value = {
      type: 'Duration',
      value: 172800
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('2d');
  });

  it('shows duration in weeks if possible', function() {
    var value = {
      type: 'Duration',
      value: 1209600
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('2w');
  });

  it('shows duration in days if not divisible by 7', function() {
    var value = {
      type: 'Duration',
      value: 1036800
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('12d');
  });

});
