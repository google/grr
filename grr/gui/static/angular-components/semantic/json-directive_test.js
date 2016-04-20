'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('json directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/semantic/json.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-json value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', function() {
    var value = {
      type: 'ZippedJSONBytes',
      value: null
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('');
  });

  it('shows error message if value is not correct json', function() {
    var value = {
      type: 'ZippedJSONBytes',
      value: '--'
    };

    var element = renderTestTemplate(value);
    expect(element.text().trim()).toMatch(/jsonerror.*:--/);
  });

  it('shows json string when it\'s a correct json string', function() {
    var value = {
      type: 'ZippedJSONBytes',
      value: '[{"foo": 42}]'
    };

    var element = renderTestTemplate(value);
    expect(element.text()).toContain('"foo": 42');
  });

  it('hides content behind a link if its longer than 1024 bytes', function() {
    var value = {
      type: 'ZippedJSONBytes',
      value: Array(1025).join('-')
    };

    var element = renderTestTemplate(value);
    expect(element.text()).not.toMatch(/base64decodeerror.*:--/);
    expect(element.text()).toContain('Show JSON...');

    browserTrigger($('a', element), 'click');
    expect(element.text()).toMatch(/jsonerror.*:--/);
    expect(element.text()).not.toContain('Show JSON...');
  });
});
