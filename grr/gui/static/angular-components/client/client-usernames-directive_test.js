'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('client usernames', function() {
  var $q, $compile, $rootScope;
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var render = function(value) {
    $rootScope.value = value;

    var template = '<grr-client-usernames value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('List client usernames with grr-semantic-value', function() {
    var usernames = {value: 'test_1 test_2 test_3'};
    var element = render(usernames);
    var directive = element.find('grr-semantic-value');
    expect(directive.scope().$eval('usernames').length).toEqual(3);
    expect(directive.scope().$eval('usernames')[0].value).toEqual('test_1');
    expect(directive.scope().$eval('usernames')[1].value).toEqual('test_2');
    expect(directive.scope().$eval('usernames')[2].value).toEqual('test_3');

    expect(directive.scope().$eval('usernames')[0].type).toEqual('RDFString');
    expect(directive.scope().$eval('usernames')[1].type).toEqual('RDFString');
    expect(directive.scope().$eval('usernames')[2].type).toEqual('RDFString');
  });

});
