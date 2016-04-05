'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.module');

describe('semantic value form directive', function() {
  var $compile, $rootScope, $q, grrSemanticFormDirectivesRegistryService;
  var grrReflectionService;

  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    grrUi.forms.semanticValueFormDirective.clearCaches();

    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrSemanticFormDirectivesRegistryService = $injector.get(
        'grrSemanticFormDirectivesRegistryService');
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

  it('destroys nested directive\'s scope if value type is changed', function() {
    var directiveFooMock = {
      directive_name: 'theFooTestDirective'
    };
    var directiveBarMock = {
      directive_name: 'theBarTestDirective'
    };

    grrSemanticFormDirectivesRegistryService.registerDirective(
        'Foo', directiveFooMock);
    grrSemanticFormDirectivesRegistryService.registerDirective(
        'Bar', directiveBarMock);

    var fooValue = {
      type: 'Foo',
      mro: ['Foo'],
      value: 'foo'
    };
    var barValue = {
      type: 'Bar',
      mro: ['Bar'],
      value: 'bar'
    };

    var element = renderTestTemplate(fooValue);
    expect($('the-foo-test-directive', element).length).toBe(1);

    var fooScope =  $('the-foo-test-directive', element).scope();
    fooScope.foo = 42;

    var firesCount = 0;
    fooScope.$watch('foo', function() {
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
