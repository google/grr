'use strict';

goog.module('grrUi.semantic.dataObjectDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('data object semantic directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/semantic/data-object.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-data-object value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows empty table when value is empty', () => {
    const element = renderTestTemplate({
      type: 'ApiDataObject',
      value: {},
    });
    expect(element.find('table').length).toBe(1);
    expect(element.find('tr').length).toBe(0);
  });

  it('shows 2 rows for a data object with two key-value pairs', () => {
    const element = renderTestTemplate({
      type: 'ApiDataObject',
      value: {
        items: [
          {
            type: 'ApiDataObjectKeyValuePair',
            value: {
              key: {
                type: 'unicode',
                value: 'Test Integer Value',
              },
              value: {
                type: 'RDFInteger',
                value: 1000,
              },
            },
          },
          {
            type: 'ApiDataObjectKeyValuePair',
            value: {
              key: {
                type: 'unicode',
                value: 'Test String Value',
              },
              value: {
                type: 'RDFString',
                value: '<some value>',
              },
            },
          }
        ],
      },
    });
    expect(element.find('table').length).toBe(1);
    expect(element.find('tr').length).toBe(2);

    expect(element.text()).toContain('Test Integer Value');
    expect(element.text()).toContain('Test String Value');

    expect(element.find('grr-semantic-value').length).toBe(2);
  });
});


exports = {};
