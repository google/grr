'use strict';

goog.module('grrUi.semantic.bytesDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {semanticModule} = goog.require('grrUi.semantic.semantic');


describe('bytes directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/semantic/bytes.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-bytes value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', () => {
    const value = {
      type: 'RDFBytes',
      value: null,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('');
  });

  it('shows error message if value is incorrectly base64-encoded', () => {
    const value = {
      type: 'RDFBytes',
      value: '--',
    };

    const element = renderTestTemplate(value);
    expect(element.text().trim()).toMatch(/base64decodeerror.*:--/);
  });

  it('converts base64-encoded value into a hex-encoded string', () => {
    const macAddress = {
      type: 'MacAddress',
      value: 'Zm9vDcg=',
    };
    const element = renderTestTemplate(macAddress);
    expect(element.text()).toContain('foo\\x0d\\xc8');
  });

  it('hides content behind a link if its longer than 1024 bytes', () => {
    const value = {
      type: 'RDFBytes',
      value: Array(1025).join('-'),
    };

    const element = renderTestTemplate(value);
    expect(element.text()).not.toMatch(/base64decodeerror.*:--/);
    expect(element.text()).toContain('Show bytes...');

    browserTriggerEvent($('a', element), 'click');
    expect(element.text()).toMatch(/base64decodeerror.*:--/);
    expect(element.text()).not.toContain('Show bytes...');
  });
});


exports = {};
