'use strict';

goog.module('grrUi.semantic.dictDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('dict semantic directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/semantic/dict.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-dict value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows empty table when value is empty', () => {
    const element = renderTestTemplate({
      type: 'dict',
      value: {},
    });
    expect(element.find('table').length).toBe(1);
    expect(element.find('tr').length).toBe(0);
  });

  it('shows 2 keys and corresponding values for value with 2 keys', () => {
    const element = renderTestTemplate({
      type: 'dict',
      value: {
        fooKey: {type: 'Foo'},
        barKey: {type: 'Bar'},
      },
    });
    expect(element.find('table').length).toBe(1);
    expect(element.find('tr').length).toBe(2);

    expect(element.text()).toContain('fooKey');
    expect(element.text()).toContain('barKey');

    expect(element.find('grr-semantic-value').length).toBe(2);
  });
});


exports = {};
