'use strict';

goog.module('grrUi.semantic.hashDigestDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('hash digest directive', () => {
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

    const template = '<grr-hash-digest value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', () => {
    const value = {
      type: 'HashDigest',
      value: null,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('');
  });

  it('shows error message if value is incorrectly base64-encoded', () => {
    const value = {
      type: 'HashDigest',
      value: '--',
    };

    const element = renderTestTemplate(value);
    expect(element.text().trim()).toMatch(/base64decodeerror.*:--/);
  });

  it('converts base64-encoded value into a hex-encoded string', () => {
    const base64EncodedHash = {
      type: 'HashDigest',
      value: 'dGVzdA==',
    };
    const element = renderTestTemplate(base64EncodedHash);
    expect(element.text()).toContain('74657374');
  });
});


exports = {};
