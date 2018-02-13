'use strict';

goog.module('grrUi.semantic.hashListDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('hash list directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-hash-list value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', () => {
    const value = {
      type: 'HashList',
      value: null,
    };
    const element = renderTestTemplate(value);
    expect(element.find('grr-hash-digest').length).toBe(0);
  });

  it('delegates single item to grr-semantic-value', () => {
    const base64EncodedHashList = {
      type: 'HashList',
      value: 'MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=',
    };
    const element = renderTestTemplate(base64EncodedHashList);
    const directive = element.find('grr-semantic-value');
    expect(angular.equals(directive.scope().$eval(directive.attr('value'))), [{
             type: 'HashDigest',
             value: 'MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=',
           }]);
  });

  it('delegates two items to grr-hash-digest', () => {
    const base64EncodedHashList = {
      type: 'HashList',
      value: 'MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE' +
          'yMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMg==',
    };
    const element = renderTestTemplate(base64EncodedHashList);
    const directive = element.find('grr-semantic-value');
    expect(angular.equals(directive.scope().$eval(directive.attr('value'))), [
      {
        type: 'HashDigest',
        value: 'MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=',
      },
      {
        type: 'HashDigest',
        value: 'MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjI=',
      },
    ]);
  });
});


exports = {};
