'use strict';

goog.module('grrUi.semantic.jsonDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {semanticModule} = goog.require('grrUi.semantic.semantic');


describe('json directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/semantic/json.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-json value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', () => {
    const value = {
      type: 'ZippedJSONBytes',
      value: null,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('');
  });

  it('shows error message if value is not correct json', () => {
    const value = {
      type: 'ZippedJSONBytes',
      value: '--',
    };

    const element = renderTestTemplate(value);
    expect(element.text().trim()).toMatch(/jsonerror.*:--/);
  });

  it('shows json string when it\'s a correct json string', () => {
    const value = {
      type: 'ZippedJSONBytes',
      value: '[{"foo": 42}]',
    };

    const element = renderTestTemplate(value);
    expect(element.text()).toContain('"foo": 42');
  });

  it('hides content behind a link if its longer than 1024 bytes', () => {
    const value = {
      type: 'ZippedJSONBytes',
      value: Array(1025).join('-'),
    };

    const element = renderTestTemplate(value);
    expect(element.text()).not.toMatch(/base64decodeerror.*:--/);
    expect(element.text()).toContain('Show JSON...');

    browserTriggerEvent($('a', element), 'click');
    expect(element.text()).toMatch(/jsonerror.*:--/);
    expect(element.text()).not.toContain('Show JSON...');
  });
});


exports = {};
