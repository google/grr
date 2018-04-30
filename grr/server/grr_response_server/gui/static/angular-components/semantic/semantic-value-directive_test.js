'use strict';

goog.module('grrUi.semantic.semanticValueDirectiveTest');

const {clearCaches, getCachedSingleValueTemplate} = goog.require('grrUi.semantic.semanticValueDirective');
const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('semantic value directive', () => {
  let $compile;
  let $q;
  let $rootScope;

  let grrSemanticValueDirectivesRegistryService;
  let grrReflectionService;

  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    clearCaches();

    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrSemanticValueDirectivesRegistryService = $injector.get(
        'grrSemanticValueDirectivesRegistryService');
    grrReflectionService = $injector.get('grrReflectionService');

    grrReflectionService.getRDFValueDescriptor = ((valueType) => {
      const deferred = $q.defer();
      deferred.resolve({
        name: valueType,
        mro: [valueType],
      });
      return deferred.promise;
    });
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-semantic-value value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is null', () => {
    const element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('');
  });

  it('does not show anything when value is undefined', () => {
    const element = renderTestTemplate(undefined);
    expect(element.text().trim()).toBe('');
  });

  it('renders plain string values', () => {
    const element = renderTestTemplate('foobar');
    expect(element.text().trim()).toBe('foobar');
  });

  it('renders plain integer values', () => {
    const element = renderTestTemplate(42);
    expect(element.text().trim()).toBe('42');
  });

  it('renders list of plain string values', () => {
    const element = renderTestTemplate(['elem1', 'elem2', 'elem3']);
    expect(element.text().trim()).toBe('elem1 elem2 elem3');
  });

  it('renders list of plain integer values', () => {
    const element = renderTestTemplate([41, 42, 43]);
    expect(element.text().trim()).toBe('41 42 43');
  });

  it('renders richly typed value with a registered directive', () => {
    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    const directiveMock = {
      directive_name: 'theTestDirective',
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'NonExistentType', directiveMock);

    const element = renderTestTemplate({
      type: 'NonExistentType',
      value: 42,
    });
    expect($('the-test-directive', element).length).toBe(1);
    expect($('the-test-directive[value="::value"]', element).length).toBe(1);
  });

  it('renders list of typed values with registered directives', () => {
    // These directives do not exist and Angular won't process them,
    // but they still will be inserted into DOM and we can check
    // that they're inserted correctly.
    const directiveMock1 = {
      directive_name: 'theTestDirective1',
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'NonExistentType1', directiveMock1);

    const directiveMock2 = {
      directive_name: 'theTestDirective2',
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'NonExistentType2', directiveMock2);

    const directiveMock3 = {
      directive_name: 'theTestDirective3',
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'NonExistentType3', directiveMock3);

    const element = renderTestTemplate([
      {
        type: 'NonExistentType1',
        value: 41,
      },
      {
        type: 'NonExistentType2',
        value: 42,
      },
      {
        type: 'NonExistentType3',
        value: 43,
      },
    ]);

    expect($('the-test-directive1', element).length).toBe(1);
    expect($('the-test-directive2', element).length).toBe(1);
    expect($('the-test-directive3', element).length).toBe(1);
  });

  it('renders typed values as strings when there\'s no handler', () => {
    const element = renderTestTemplate({
      type: 'NonExistentType',
      value: 42,
    });

    expect(element.text().trim()).toBe('42');
  });

  it('respects type override done with grr-semantic-value-registry-override',
     () => {
       const directiveMock = {
         directive_name: 'theTestDirective',
       };
       grrSemanticValueDirectivesRegistryService.registerDirective(
           'SomeType', directiveMock);

       // This directive does not exist and Angular won't process it,
       // but it still will be inserted into DOM and we can check
       // that it's inserted correctly.
       const overrideDirectiveMock = {
         directive_name: 'theTestDirectiveOverride',
       };
       $rootScope.override = overrideDirectiveMock;

       $rootScope.value = {
         type: 'SomeType',
         value: 42,
       };
       const template = '<grr-semantic-value-registry-override ' +
           'map="{\'SomeType\': override}">' +
           '<grr-semantic-value value="value"></grr-semantic-value>' +
           '</grr-semantic-value-registry-override>';
       const element = $compile(template)($rootScope);
       $rootScope.$apply();

       expect($('the-test-directive-override', element).length).toBe(1);
     });

  it('respects the override even if an RDF type was rendered once before',
     () => {
       const directiveMock = {
         directive_name: 'theTestDirective',
       };
       grrSemanticValueDirectivesRegistryService.registerDirective(
           'SomeType', directiveMock);

       let element = renderTestTemplate({
         type: 'SomeType',
         value: 42,
       });
       expect($('the-test-directive', element).length).toBe(1);

       // This directive does not exist and Angular won't process it,
       // but it still will be inserted into DOM and we can check
       // that it's inserted correctly.
       const overrideDirectiveMock = {
         directive_name: 'theTestDirectiveOverride',
       };
       $rootScope.override = overrideDirectiveMock;

       const template = '<grr-semantic-value-registry-override ' +
           'map="{\'SomeType\': override}">' +
           '<grr-semantic-value value="value"></grr-semantic-value>' +
           '</grr-semantic-value-registry-override>';
       element = $compile(template)($rootScope);
       $rootScope.$apply();

       expect($('the-test-directive-override', element).length).toBe(1);
     });

  it('caches templates for overrides using unique keys', () => {
    const directiveMock = {
      directive_name: 'theTestDirective',
    };
    grrSemanticValueDirectivesRegistryService.registerDirective(
        'SomeType', directiveMock);

    let element = renderTestTemplate({
      type: 'SomeType',
      value: 42,
    });
    expect($('the-test-directive', element).length).toBe(1);

    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    const overrideDirectiveMock = {
      directive_name: 'theTestDirectiveOverride',
    };
    $rootScope.override = overrideDirectiveMock;

    const template = '<grr-semantic-value-registry-override ' +
        'map="{\'SomeType\': override, \'AnotherType\': override}">' +
        '<grr-semantic-value value="value"></grr-semantic-value>' +
        '</grr-semantic-value-registry-override>';
    element = $compile(template)($rootScope);
    $rootScope.$apply();

    expect(getCachedSingleValueTemplate('SomeType')).toBeDefined();
    expect(getCachedSingleValueTemplate(
               'SomeType:AnotherType_theTestDirectiveOverride:' +
               'SomeType_theTestDirectiveOverride'))
        .toBeDefined();
  });
});


exports = {};
