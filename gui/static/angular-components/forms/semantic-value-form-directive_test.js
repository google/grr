'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.module');

describe('semantic value form directive', function() {
  var $compile, $rootScope;
  var grrSemanticFormDirectivesRegistryService;

  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    grrUi.forms.semanticValueFormDirective.clearCaches();

    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    grrSemanticFormDirectivesRegistryService = $injector.get(
        'grrSemanticFormDirectivesRegistryService');
  }));

  var renderTestTemplate = function(value, metadata) {
    $rootScope.value = value;
    $rootScope.metadata = metadata;

    var template = '<grr-form-value value="value" metadata="metadata" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows error message if no corresponding directive found', function() {
    var fooValue = {
      type: 'Foo',
      mro: ['Foo'],
      value: 'foo'
    };

    var element = renderTestTemplate(fooValue);
    expect(element.text()).toContain('No directive for type: Foo');
  });

  it('renders registered type with a corresponding directive', function() {
    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    var directiveMock = {
      directive_name: 'theTestDirective'
    };

    grrSemanticFormDirectivesRegistryService.registerDirective(
        'Foo', directiveMock);
    var fooValue = {
      type: 'Foo',
      mro: ['Foo'],
      value: 'foo'
    };
    var metadata = {
      foo: 'bar'
    };

    var element = renderTestTemplate(fooValue);
    expect($('the-test-directive', element).length).toBe(1);
    // Check that registered directive has "value" attribute specified.
    expect($('the-test-directive[value]', element).length).toBe(1);
    // Check that metadata are passed to the nested directive.
    expect($('the-test-directive[metadata]', element).length).toBe(1);
  });

});
