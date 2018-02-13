'use strict';

goog.module('grrUi.semantic.encryptionKeyDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {stringifyEncryptionKey} = goog.require('grrUi.semantic.encryptionKeyDirective');
const {testsModule} = goog.require('grrUi.tests');


describe('encryption key directive', () => {
  describe('stringifyEncryptionKey()', () => {

    it('converts base64 encoded string of zeroes to a hex-string', () => {
      expect(stringifyEncryptionKey('AAAAAA==')).toBe('00000000');
    });

    it('converts sample base64 encoded string to a hex-string', () => {
      expect(stringifyEncryptionKey('AAABAgMEBQYHCAkKCwwNDg8Q')).toBe(
          '00000102030405060708090a0b0c0d0e0f10');
    });
  });

  let $compile;
  let $rootScope;


  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-encryption-key value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', () => {
    const element = renderTestTemplate(undefined);
    expect(element.text().trim()).toBe('');
  });

  it('shows hex-stringified bytes when value is not empty', () => {
    const element = renderTestTemplate({
      type: 'EncryptionKey',
      value: 'AAABAgMEBQYHCAkKCwwNDg8Q',
    });
    expect(element.text().trim()).toBe('00000102030405060708090a0b0c0d0e0f10');
  });
});


exports = {};
