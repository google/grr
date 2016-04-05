'use strict';

goog.require('grrUi.semantic.encryptionKeyDirective.stringifyEncryptionKey');
goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('encryption key directive', function() {

  describe('stringifyEncryptionKey()', function() {
    var stringifyEncryptionKey =
        grrUi.semantic.encryptionKeyDirective.stringifyEncryptionKey;

    it('converts base64 encoded string of zeroes to a hex-string', function() {
      expect(stringifyEncryptionKey('AAAAAA==')).toBe('00000000');
    });

    it('converts sample base64 encoded string to a hex-string', function() {
      expect(stringifyEncryptionKey('AAABAgMEBQYHCAkKCwwNDg8Q')).toBe(
          '00000102030405060708090a0b0c0d0e0f10');
    });
  });

  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-encryption-key value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', function() {
    var element = renderTestTemplate(undefined);
    expect(element.text().trim()).toBe('');
  });

  it('shows hex-stringified bytes when value is not empty', function() {
    var element = renderTestTemplate({
      type: 'EncryptionKey',
      value: 'AAABAgMEBQYHCAkKCwwNDg8Q'
    });
    expect(element.text().trim()).toBe('00000102030405060708090a0b0c0d0e0f10');
  });
});
