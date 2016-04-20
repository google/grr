'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('bytes directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/semantic/bytes.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-bytes value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', function() {
    var value = {
      type: 'RDFBytes',
      value: null
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('');
  });

  it('shows error message if value is incorrectly base64-encoded', function() {
    var value = {
      type: 'RDFBytes',
      value: '--'
    };

    var element = renderTestTemplate(value);
    expect(element.text().trim()).toMatch(/base64decodeerror.*:--/);
  });

  it('converts base64-encoded value into a hex-encoded string', function() {
    var macAddress = {
      type: 'MacAddress',
      value: 'Zm9vDcg='
    };
    var element = renderTestTemplate(macAddress);
    expect(element.text()).toContain('foo\\x0d\\xc8');
  });

  it('hides content behind a link if its longer than 1024 bytes', function() {
    var value = {
      type: 'RDFBytes',
      value: Array(1025).join('-')
    };

    var element = renderTestTemplate(value);
    expect(element.text()).not.toMatch(/base64decodeerror.*:--/);
    expect(element.text()).toContain('Show bytes...');

    browserTrigger($('a', element), 'click');
    expect(element.text()).toMatch(/base64decodeerror.*:--/);
    expect(element.text()).not.toContain('Show bytes...');
  });
});
