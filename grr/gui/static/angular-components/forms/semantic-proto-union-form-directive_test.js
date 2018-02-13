'use strict';

goog.module('grrUi.forms.semanticProtoUnionFormDirectiveTest');

const {formsModule} = goog.require('grrUi.forms.forms');
const {testsModule} = goog.require('grrUi.tests');


describe('semantic proto union form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let descriptor;
  let grrReflectionService;


  beforeEach(module('/static/angular-components/forms/semantic-proto-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-union-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-single-field-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-repeated-field-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    grrReflectionService.getRDFValueDescriptor = ((valueType) => {
      const deferred = $q.defer();
      deferred.resolve({
        name: valueType,
        mro: [valueType],
      });
      return deferred.promise;
    });

    descriptor = {
      'default': {
        'mro': ['Foo', 'RDFProtoStruct'],
        'type': 'Foo',
        'value': {},
      },
      'doc': 'This is a structure Foo.',
      'union_field': 'type',
      'fields': [
        {
          'default': {
            'mro': ['PrimitiveType'],
            'type': 'PrimitiveType',
            'value': '',
          },
          'index': 1,
          'name': 'type',
          'repeated': false,
          'type': 'PrimitiveType',
        },
        {
          'default': {
            'mro': ['PrimitiveTypeFoo'],
            'type': 'PrimitiveTypeFoo',
            'value': 'foo',
          },
          'index': 2,
          'name': 'foo',
          'repeated': false,
          'type': 'PrimitiveTypeFoo',
        },
        {
          'default': {
            'mro': ['PrimitiveTypeBar'],
            'type': 'PrimitiveTypeBar',
            'value': 'bar',
          },
          'index': 3,
          'name': 'bar',
          'repeated': false,
          'type': 'PrimitiveTypeBar',
        },
      ],
    };
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;
    $rootScope.descriptor = descriptor;

    const template = '<grr-form-proto-union value="value" ' +
        'descriptor="descriptor" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('displays field based on union field value', () => {
    const value = {
      type: 'Foo',
      mro: ['Foo'],
      value: {
        type: {
          type: 'PrimitiveType',
          mro: ['PrimitiveType'],
          value: 'foo',
        },
        foo: {
          type: 'PrimitiveTypeFoo',
          mro: ['PrimitiveTypeFoo'],
          value: 42,
        },
        bar: {
          type: 'PrimitiveTypeBar',
          mro: ['PrimitiveTypeBar'],
          value: 43,
        },
      },
    };
    const element = renderTestTemplate(value);

    // Check that only the field 'foo' is displayed. As we expect no directives
    // to be registered for PrimitiveTypeFoo and PrimitiveTypeBar, we check
    // for the stub message produced by grr-form-value.
    expect(element.text()).toContain('No directive for type: PrimitiveTypeFoo');
    expect(element.text()).not.toContain(
        'No directive for type: PrimitiveTypeBar');

    value.value.type.value = 'bar';
    $rootScope.$apply();

    // Check that form got updated and now field 'bar' is displayed.
    expect(element.text()).toContain('No directive for type: PrimitiveTypeBar');
    expect(element.text()).not.toContain(
        'No directive for type: PrimitiveTypeFoo');
  });

  it('resets entered data when union type is changed', () => {
    const value = {
      type: 'Foo',
      mro: ['Foo'],
      value: {
        type: {
          type: 'PrimitiveType',
          mro: ['PrimitiveType'],
          value: 'foo',
        },
        foo: {
          type: 'PrimitiveTypeFoo',
          mro: ['PrimitiveTypeFoo'],
        },
        bar: {
          type: 'PrimitiveTypeBar',
          mro: ['PrimitiveTypeBar'],
        },
      },
    };
    renderTestTemplate(value);
    $rootScope.$apply();

    value.value.foo.value = 42;
    $rootScope.$apply();
    expect(value.value.foo.value).toBe(42);

    value.value.type.value = 'bar';
    $rootScope.$apply();
    expect(value.value.foo.value).toEqual({});
  });
});


exports = {};
