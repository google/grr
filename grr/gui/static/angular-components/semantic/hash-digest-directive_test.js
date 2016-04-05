'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('hash digest directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-hash-digest value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', function() {
    var value = {
      type: 'HashDigest',
      value: null
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('');
  });

  it('shows error message if value is incorrectly base64-encoded', function() {
    var value = {
      type: 'HashDigest',
      value: '--'
    };

    var element = renderTestTemplate(value);
    expect(element.text().trim()).toMatch(/base64decodeerror.*:--/);
  });

  it('converts base64-encoded value into a hex-encoded string', function() {
    var base64EncodedHash = {
      type: 'HashDigest',
      value: 'dGVzdA=='
    };
    var element = renderTestTemplate(base64EncodedHash);
    expect(element.text()).toContain('74657374');
  });

});
