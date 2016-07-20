'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

describe('hash list directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-hash-list value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when value is empty', function() {
    var value = {
      type: 'HashList',
      value: null
    };
    var element = renderTestTemplate(value);
    expect(element.find('grr-hash-digest').length).toBe(0);
  });

  it('delegates single item to grr-semantic-value', function() {
    var base64EncodedHashList = {
      type: 'HashList',
      value: 'MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE='
    };
    var element = renderTestTemplate(base64EncodedHashList);
    var directive = element.find('grr-semantic-value');
    expect(angular.equals(directive.scope().$eval(directive.attr('value'))),
           [{
             type: 'HashDigest',
             value: 'MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE='
           }]);
  });

  it('delegates two items to grr-hash-digest', function() {
    var base64EncodedHashList = {
      type: 'HashList',
      value: 'MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE' +
          'yMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMg==',
    };
    var element = renderTestTemplate(base64EncodedHashList);
    var directive = element.find('grr-semantic-value');
    expect(angular.equals(directive.scope().$eval(directive.attr('value'))),
           [
             {
               type: 'HashDigest',
               value: 'MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE='
             },
             {
               type: 'HashDigest',
               value: 'MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjI='
             }
           ]);
  });

});
