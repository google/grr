'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.semantic.semanticValueDirective.clearCaches');
goog.require('grrUi.tests.module');

goog.scope(function() {

var SemanticDirectivesRegistry = grrUi.semantic.SemanticDirectivesRegistry;

describe('semantic value directive', function() {
  var $compile, $rootScope, $q;
  var grrSemanticValueDirectivesRegistryService;
  var grrReflectionService;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    grrUi.semantic.semanticValueDirective.clearCaches();

    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrSemanticValueDirectivesRegistryService = $injector.get(
        'grrSemanticValueDirectivesRegistryService');
    grrReflectionService = $injector.get('grrReflectionService');

    grrReflectionService.getRDFValueDescriptor = function(valueType) {
      var deferred = $q.defer();
      deferred.resolve({
        name: valueType,
        mro: [valueType]
      });
      return deferred.promise;
    };
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-semantic-value value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is null', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('');
  });

  it('does not show anything when value is undefined', function() {
    var element = renderTestTemplate(undefined);
    expect(element.text().trim()).toBe('');
  });

  it('renders plain string values', function() {
    var element = renderTestTemplate('foobar');
    expect(element.text().trim()).toBe('foobar');
  });

  it('renders plain integer values', function() {
    var element = renderTestTemplate(42);
    expect(element.text().trim()).toBe('42');
  });

  it('renders list of plain string values', function() {
    var element = renderTestTemplate(['elem1', 'elem2', 'elem3']);
    expect(element.text().trim()).toBe('elem1 elem2 elem3');
  });

  it('renders list of plain integer values', function() {
    var element = renderTestTemplate([41, 42, 43]);
    expect(element.text().trim()).toBe('41 42 43');
  });

  it('renders richly typed value with a registered directive', function() {
    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    var directiveMock = {
      directive_name: 'theTestDirective'
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'NonExistentType', directiveMock);

    var element = renderTestTemplate({
      type: 'NonExistentType',
      value: 42
    });
    expect($('the-test-directive', element).length).toBe(1);
    expect($('the-test-directive[value="::value"]', element).length).toBe(1);
  });

  it('renders list of typed values with registered directives', function() {
    // These directives do not exist and Angular won't process them,
    // but they still will be inserted into DOM and we can check
    // that they're inserted correctly.
    var directiveMock1 = {
      directive_name: 'theTestDirective1'
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'NonExistentType1', directiveMock1);

    var directiveMock2 = {
      directive_name: 'theTestDirective2'
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'NonExistentType2', directiveMock2);

    var directiveMock3 = {
      directive_name: 'theTestDirective3'
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'NonExistentType3', directiveMock3);

    var element = renderTestTemplate([
      {
        type: 'NonExistentType1',
        value: 41
      },
      {
        type: 'NonExistentType2',
        value: 42
      },
      {
        type: 'NonExistentType3',
        value: 43
      }
    ]);

    expect($('the-test-directive1', element).length).toBe(1);
    expect($('the-test-directive2', element).length).toBe(1);
    expect($('the-test-directive3', element).length).toBe(1);
  });

  it('renders typed values as strings when there\'s no handler', function() {
    var element = renderTestTemplate({
      type: 'NonExistentType',
      value: 42
    });

    expect(element.text().trim()).toBe('42');
  });

  it('respects type override done with grr-semantic-value-registry-override', function() {
    var directiveMock = {
      directive_name: 'theTestDirective'
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'SomeType', directiveMock);

    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    var overrideDirectiveMock = {
      directive_name: 'theTestDirectiveOverride'
    };
    $rootScope.override = overrideDirectiveMock;

    $rootScope.value = {
      type: 'SomeType',
      value: 42
    };
    var template = '<grr-semantic-value-registry-override ' +
        'map="{\'SomeType\': override}">' +
        '<grr-semantic-value value="value"></grr-semantic-value>' +
        '</grr-semantic-value-registry-override>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    expect($('the-test-directive-override', element).length).toBe(1);
  });

  it('respects the override even if an RDF type was rendered once before', function() {
    var directiveMock = {
      directive_name: 'theTestDirective'
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'SomeType', directiveMock);

    var element = renderTestTemplate({
      type: 'SomeType',
      value: 42
    });
    expect($('the-test-directive', element).length).toBe(1);

    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    var overrideDirectiveMock = {
      directive_name: 'theTestDirectiveOverride'
    };
    $rootScope.override = overrideDirectiveMock;

    var template = '<grr-semantic-value-registry-override ' +
        'map="{\'SomeType\': override}">' +
        '<grr-semantic-value value="value"></grr-semantic-value>' +
        '</grr-semantic-value-registry-override>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    expect($('the-test-directive-override', element).length).toBe(1);
  });

  it('caches templates for overrides using unique keys', function() {
    var directiveMock = {
      directive_name: 'theTestDirective'
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'SomeType', directiveMock);

    var element = renderTestTemplate({
      type: 'SomeType',
      value: 42
    });
    expect($('the-test-directive', element).length).toBe(1);

    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    var overrideDirectiveMock = {
      directive_name: 'theTestDirectiveOverride'
    };
    $rootScope.override = overrideDirectiveMock;

    var template = '<grr-semantic-value-registry-override ' +
        'map="{\'SomeType\': override, \'AnotherType\': override}">' +
        '<grr-semantic-value value="value"></grr-semantic-value>' +
        '</grr-semantic-value-registry-override>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    var cache = grrUi.semantic.semanticValueDirective.singleValueTemplateCache;
    expect(Object.keys(cache).length).toBe(2);
    expect(cache['SomeType']).toBeDefined();
    expect(cache['SomeType:AnotherType_theTestDirectiveOverride:' +
                 'SomeType_theTestDirectiveOverride']).toBeDefined();
  });
});

});  // goog.scope
