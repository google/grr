'use strict';

goog.module('grrUi.client.clientUsernamesDirectiveTest');

const {clientModule} = goog.require('grrUi.client.client');
const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('client usernames', () => {
  let $compile;
  let $rootScope;

  beforeEach(module(clientModule.name));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = (value) => {
    $rootScope.value = value;

    const template = '<grr-client-usernames value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('List client usernames with grr-semantic-value', () => {
    const usernames = {value: 'test_1 test_2 test_3'};
    const element = render(usernames);
    const directive = element.find('grr-semantic-value');
    expect(directive.scope().$eval('usernames').length).toEqual(3);
    expect(directive.scope().$eval('usernames')[0].value).toEqual('test_1');
    expect(directive.scope().$eval('usernames')[1].value).toEqual('test_2');
    expect(directive.scope().$eval('usernames')[2].value).toEqual('test_3');

    expect(directive.scope().$eval('usernames')[0].type).toEqual('RDFString');
    expect(directive.scope().$eval('usernames')[1].type).toEqual('RDFString');
    expect(directive.scope().$eval('usernames')[2].type).toEqual('RDFString');
  });
});


exports = {};
