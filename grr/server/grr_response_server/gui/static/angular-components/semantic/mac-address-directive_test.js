'use strict';

goog.module('grrUi.semantic.macAddressDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('mac address directive', () => {
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

    const template = '<grr-mac-address value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "-" when value is empty', () => {
    const macAddress = {
      type: 'MacAddress',
      value: null,
    };
    const element = renderTestTemplate(macAddress);
    expect(element.text().trim()).toBe('-');
  });

  it('expands base64-encoded value into a human-readable string', () => {
    const macAddress = {
      type: 'MacAddress',
      value: '+BZUBnli',
    };
    const element = renderTestTemplate(macAddress);
    expect(element.text()).toContain('f8:16:54:06:79:62');
  });
});


exports = {};
