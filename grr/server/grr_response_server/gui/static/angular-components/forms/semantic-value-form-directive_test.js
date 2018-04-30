'use strict';

goog.module('grrUi.forms.semanticValueFormDirectiveTest');

const {clearCaches} = goog.require('grrUi.forms.semanticValueFormDirective');
const {formsModule} = goog.require('grrUi.forms.forms');
const {testsModule} = goog.require('grrUi.tests');


describe('semantic value form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrSemanticFormDirectivesRegistryService;

  let grrReflectionService;

  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    clearCaches();

    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrSemanticFormDirectivesRegistryService = $injector.get(
        'grrSemanticFormDirectivesRegistryService');
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

  const renderTestTemplate = (value, metadata) => {
    $rootScope.value = value;
    $rootScope.metadata = metadata;

    const template = '<grr-form-value value="value" metadata="metadata" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows error message if no corresponding directive found', () => {
    const fooValue = {
      type: 'Foo',
      mro: ['Foo'],
      value: 'foo',
    };

    const element = renderTestTemplate(fooValue);
    expect(element.text()).toContain('No directive for type: Foo');
  });

  it('renders registered type with a corresponding directive', () => {
    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    const directiveMock = {
      directive_name: 'theTestDirective',
    };

    grrSemanticFormDirectivesRegistryService.registerDirective(
        'Foo', directiveMock);
    const fooValue = {
      type: 'Foo',
      mro: ['Foo'],
      value: 'foo',
    };

    const element = renderTestTemplate(fooValue);
    expect($('the-test-directive', element).length).toBe(1);
    // Check that registered directive has "value" attribute specified.
    expect($('the-test-directive[value]', element).length).toBe(1);
    // Check that metadata are passed to the nested directive.
    expect($('the-test-directive[metadata]', element).length).toBe(1);
  });

  it('destroys nested directive\'s scope if value type is changed', () => {
    const directiveFooMock = {
      directive_name: 'theFooTestDirective',
    };
    const directiveBarMock = {
      directive_name: 'theBarTestDirective',
    };

    grrSemanticFormDirectivesRegistryService.registerDirective(
        'Foo', directiveFooMock);
    grrSemanticFormDirectivesRegistryService.registerDirective(
        'Bar', directiveBarMock);

    const fooValue = {
      type: 'Foo',
      mro: ['Foo'],
      value: 'foo',
    };
    const barValue = {
      type: 'Bar',
      mro: ['Bar'],
      value: 'bar',
    };

    const element = renderTestTemplate(fooValue);
    expect($('the-foo-test-directive', element).length).toBe(1);

    const fooScope = $('the-foo-test-directive', element).scope();
    fooScope.foo = 42;

    let firesCount = 0;
    fooScope.$watch('foo', () => {
      firesCount += 1;
    });

    // Watcher should be called once when it's installed.
    $rootScope.$apply();
    expect(firesCount).toBe(1);

    // Then it should be called when the value changes.
    fooScope.foo = 43;
    $rootScope.$apply();
    expect(firesCount).toBe(2);

    // Change the type of the value handled by directive. This should trigger
    // it to replace the nested directive.
    angular.extend(fooValue, barValue);
    $rootScope.$apply();
    expect($('the-bar-test-directive', element).length).toBe(1);

    // Watchers installed on the directive's scope that corresponds to the
    // previous value type (the-foo-test-directive), shouldn't be fired,
    // as this scope is supposed to be destroyed.
    fooScope.foo = 44;
    $rootScope.$apply();
    expect(firesCount).toBe(2);
  });
});


exports = {};
