goog.module('grrUi.forms.semanticProtoFormDirectiveTest');
goog.setTestOnly();

const {browserTriggerEvent, stubDirective, testsModule} = goog.require('grrUi.tests');
const {clearCaches} = goog.require('grrUi.forms.semanticValueFormDirective');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('semantic proto form directive', () => {
  let $compile;
  let $q;
  let $rootScope;

  let grrReflectionServiceMock;

  beforeEach(module('/static/angular-components/forms/semantic-proto-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  angular.forEach(
      [
        'grrFormProtoSingleField', 'grrFormProtoRepeatedField',
        'grrFormProtoUnion'
      ],
      (directiveName) => {
        stubDirective(directiveName);
      });

  beforeEach(module(($provide) => {
    grrReflectionServiceMock = {
      getRDFValueDescriptor: function() {},
    };

    $provide.factory('grrReflectionService', () => grrReflectionServiceMock);
  }));

  beforeEach(inject(($injector) => {
    clearCaches();

    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
  }));

  const renderTestTemplate = (value, metadata, hiddenFields) => {
    $rootScope.value = value;
    $rootScope.metadata = metadata;
    $rootScope.hiddenFields = hiddenFields;

    const template = '<grr-form-proto value="value" metadata="metadata" ' +
        'hidden-fields="hiddenFields" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  describe('form for structure with 3 primitive fields', () => {
    let defaultFooStructValue;

    beforeEach(() => {
      defaultFooStructValue = {
        type: 'Foo',
        mro: ['Foo', 'RDFProtoStruct'],
        value: {},
      };

      // Reflection service is a mock. Stub out the getRDFValueDescriptor method
      // and return a promise with the reflection data.
      const data = {
        'Foo': {
          'default': {
            'type': 'Foo',
            'value': {},
          },
          'doc': 'This is a structure Foo.',
          'fields': [
            {
              'doc': 'Field 1 description.',
              'dynamic': false,
              'friendly_name': 'Field 1',
              'index': 1,
              'name': 'field_1',
              'repeated': false,
              'type': 'PrimitiveType',
            },
            {
              'default': {
                'type': 'PrimitiveType',
                'value': 'a foo bar',
              },
              'doc': 'Field 2 description.',
              'dynamic': false,
              'friendly_name': 'Field 2',
              'index': 1,
              'name': 'field_2',
              'repeated': false,
              'type': 'PrimitiveType',
            },
            {
              'default': {
                'type': 'PrimitiveType',
                'value': '',
              },
              'doc': 'Field 3 description.',
              'dynamic': false,
              'friendly_name': 'Field 3',
              'index': 1,
              'name': 'field_3',
              'repeated': false,
              'type': 'PrimitiveType',
            },
          ],
          'kind': 'struct',
          'name': 'Foo',
          'mro': ['Foo', 'RDFProtoStruct'],
        },
        'PrimitiveType': {
          'default': {
            'type': 'PrimitiveType',
            'value': '',
          },
          'doc': 'Test primitive type description.',
          'kind': 'primitive',
          'name': 'PrimitiveType',
          'mro': ['PrimitiveType'],
        },
      };

      const reflectionDeferred = $q.defer();
      reflectionDeferred.resolve(data);
      spyOn(grrReflectionServiceMock, 'getRDFValueDescriptor')
          .and.callFake((type, opt_withDeps) => {
            const reflectionDeferred = $q.defer();
            reflectionDeferred.resolve(opt_withDeps ? data : data[type]);
            return reflectionDeferred.promise;
          });
    });

    it('renders a form for structure with 3 primitive fields', () => {
      const element = renderTestTemplate(defaultFooStructValue);

      // Check that for every primitive field a grr-form-proto-single-field
      // directive is created.
      expect(element.find('grr-form-proto-single-field').length).toBe(3);
    });

    it('does not overwrite field prefilled with non-default value', () => {
      const fooValue = defaultFooStructValue;
      fooValue.value = {
        field_2: {
          type: 'PrimitiveType',
          value: '42',
        },
      };
      renderTestTemplate(fooValue);

      expect(fooValue.value).toEqual({
        field_2: {
          type: 'PrimitiveType',
          value: '42',
        },
      });
    });

    it('does not erase the field with default value prefilled with default ' +
           'field value not equal to the default type value',
       () => {
         const fooValue = defaultFooStructValue;
         fooValue.value = {
           field_2: {
             type: 'PrimitiveType',
             value: 'a foo bar',
           },
         };
         renderTestTemplate(fooValue);

         expect(fooValue.value).toEqual({
           field_2: {
             type: 'PrimitiveType',
             value: 'a foo bar',
           },
         });
       });

    it('erases the field with default value prefilled with default field ' +
           'value equal to the default type value',
       () => {
         const fooValue = defaultFooStructValue;
         fooValue.value = {
           field_3: {
             type: 'PrimitiveType',
             value: '',
           },
         };
         renderTestTemplate(fooValue);

         expect(fooValue.value).toEqual({});
       });

    it('erases the field without default prefilled with default type ' +
           'value',
       () => {
         const fooValue = defaultFooStructValue;
         fooValue.value = {
           field_1: {
             type: 'PrimitiveType',
             value: '',
           },
         };
         renderTestTemplate(fooValue);

         expect(fooValue.value).toEqual({});
       });

    it('does not erase hidden fields', () => {
      const fooValue = defaultFooStructValue;
      fooValue.value = {
        field_1: {
          type: 'PrimitiveType',
          value: '',
        },
      };
      renderTestTemplate(fooValue, undefined, ['field_1']);

      expect(fooValue.value).toEqual({
        field_1: {
          type: 'PrimitiveType',
          value: '',
        },
      });
    });

    it('does not render fields listed in hidden-fields argument', () => {
      const element =
          renderTestTemplate(defaultFooStructValue, undefined, ['field_1']);

      expect(element.find('grr-form-proto-single-field').length).toBe(2);

      // Check that rendered fields are field_2 and field_3 only.
      let field = element.find('grr-form-proto-single-field:nth(0)');
      expect(field.scope().$eval(field.attr('value'))).toEqual({
        type: 'PrimitiveType',
        value: 'a foo bar',
      });

      field = element.find('grr-form-proto-single-field:nth(1)');
      expect(field.scope().$eval(field.attr('value'))).toEqual({
        type: 'PrimitiveType',
        value: '',
      });
    });

    it('does not prefill the model with defaults', () => {
      const fooValue = defaultFooStructValue;
      renderTestTemplate(fooValue);

      expect(fooValue.value).toEqual({});
    });

    it('prefills nested form elements with defaults', () => {
      const fooValue = defaultFooStructValue;
      const element = renderTestTemplate(fooValue);

      let field = element.find('grr-form-proto-single-field:nth(0)');
      expect(field.scope().$eval(field.attr('value'))).toEqual({
        type: 'PrimitiveType',
        value: '',
      });

      field = element.find('grr-form-proto-single-field:nth(1)');
      expect(field.scope().$eval(field.attr('value'))).toEqual({
        type: 'PrimitiveType',
        value: 'a foo bar',
      });

      field = element.find('grr-form-proto-single-field:nth(2)');
      expect(field.scope().$eval(field.attr('value'))).toEqual({
        type: 'PrimitiveType',
        value: '',
      });
    });

    it('updates model when a field is changed', () => {
      const fooValue = defaultFooStructValue;
      const element = renderTestTemplate(fooValue);

      const field = element.find('grr-form-proto-single-field:nth(0)');
      const fieldValue = field.scope().$eval(field.attr('value'));
      fieldValue.value = '42';

      $rootScope.$apply();

      expect(fooValue.value).toEqual({
        field_1: {
          type: 'PrimitiveType',
          value: '42',
        },
      });
    });

    it('updates fields when value.field_1 is changed externally', () => {
      const fooValue = defaultFooStructValue;
      const element = renderTestTemplate(fooValue);

      let field = element.find('grr-form-proto-single-field:nth(0)');
      let fieldValue = field.scope().$eval(field.attr('value'));
      expect(fieldValue['value']).toBe('');

      fooValue['value']['field_1'] = {
        type: 'PrimitiveType',
        value: 'foo',
      };

      $rootScope.$apply();

      field = element.find('grr-form-proto-single-field:nth(0)');
      fieldValue = field.scope().$eval(field.attr('value'));
      expect(fieldValue).toEqual({
        type: 'PrimitiveType',
        value: 'foo',
      });
    });

    it('with set fields: updates only changed on external change', () => {
      const fooValue = defaultFooStructValue;
      fooValue['value']['field_1'] = {
        type: 'PrimitiveType',
        value: 'foo',
      };
      fooValue['value']['field_2'] = {
        type: 'PrimitiveType',
        value: 'bar',
      };
      const element = renderTestTemplate(fooValue);

      const field1 = element.find('grr-form-proto-single-field:nth(0)');
      const field2 = element.find('grr-form-proto-single-field:nth(1)');
      const field1Value = field1.scope().$eval(field1.attr('value'));
      const field2Value = field2.scope().$eval(field2.attr('value'));

      fooValue['value']['field_1'] = {
        type: 'PrimitiveType',
        value: 'fooNew',
      };

      $rootScope.$apply();

      const field1New = element.find('grr-form-proto-single-field:nth(0)');
      const field2New = element.find('grr-form-proto-single-field:nth(1)');
      const field1ValueNew = field1New.scope().$eval(field1New.attr('value'));
      const field2ValueNew = field2New.scope().$eval(field2New.attr('value'));

      // Only field1 value has to actually change since the field got
      // updated. field2 should simply stay the same.
      expect(field1ValueNew).not.toBe(field1Value);
      expect(field2ValueNew).toBe(field2Value);
    });

    it('with unset fields: updates only changed on external change', () => {
      const fooValue = defaultFooStructValue;
      const element = renderTestTemplate(fooValue);

      const field1 = element.find('grr-form-proto-single-field:nth(0)');
      const field2 = element.find('grr-form-proto-single-field:nth(1)');
      const field1Value = field1.scope().$eval(field1.attr('value'));
      const field2Value = field2.scope().$eval(field2.attr('value'));

      fooValue['value']['field_1'] = {
        type: 'PrimitiveType',
        value: 'foo',
      };

      $rootScope.$apply();

      const field1New = element.find('grr-form-proto-single-field:nth(0)');
      const field2New = element.find('grr-form-proto-single-field:nth(1)');
      const field1ValueNew = field1New.scope().$eval(field1New.attr('value'));
      const field2ValueNew = field2New.scope().$eval(field2New.attr('value'));

      // Only field1 value has to actually change since the field got
      // updated. field2 should simply stay the same.
      expect(field1ValueNew).not.toBe(field1Value);
      expect(field2ValueNew).toBe(field2Value);
    });

    it('updates fields when value.field_1 is cleared externally', () => {
      const fooValue = defaultFooStructValue;
      fooValue['value']['field_1'] = {
        type: 'PrimitiveType',
        value: 'foo',
      };
      const element = renderTestTemplate(fooValue);

      let field = element.find('grr-form-proto-single-field:nth(0)');
      let fieldValue = field.scope().$eval(field.attr('value'));
      expect(fieldValue['value']).toBe('foo');

      fooValue['value']['field_1'] = undefined;

      $rootScope.$apply();

      field = element.find('grr-form-proto-single-field:nth(0)');
      fieldValue = field.scope().$eval(field.attr('value'));
      expect(fieldValue).toEqual({
        type: 'PrimitiveType',
        value: '',
      });
    });

    const icon =
        ((element, iconName) => element.find(`i.glyphicon-${iconName}`));

    const expectIcon = ((element, iconName) => {
      expect(icon(element, iconName).length).toBe(1);
    });

    const expectNoIcon = ((element, iconName) => {
      expect(icon(element, iconName).length).toBe(0);
    });

    it('does not render collapse/expand icon if depth is not set', () => {
      const element =
          renderTestTemplate(defaultFooStructValue, {depth: undefined});

      expectNoIcon(element, 'plus');
    });

    it('does not render collapse/expand icon if depth is 0 or 1', () => {
      let element = renderTestTemplate(defaultFooStructValue, {depth: 0});
      expectNoIcon(element, 'plus');

      element = renderTestTemplate(defaultFooStructValue, {depth: 1});
      expectNoIcon(element, 'plus');
    });

    it('renders as collapsed if metadata.depth is 2', () => {
      const element = renderTestTemplate(defaultFooStructValue, {depth: 2});
      expectIcon(element, 'plus');
    });

    it('expands if collapsed plus icons is clicked', () => {
      const element = renderTestTemplate(defaultFooStructValue, {depth: 2});
      // Nothing is shown by default, field is collapsed.
      expect(element.find('grr-form-proto-single-field').length).toBe(0);

      // Click on the '+' icon to expand it.
      browserTriggerEvent(icon(element, 'plus'), 'click');
      // Check that fields got displayed.
      expect(element.find('grr-form-proto-single-field').length).toBe(3);
      // Check that '+' icon became '-' icon.
      expectNoIcon(element, 'plus');
      expectIcon(element, 'minus');
    });

    it('collapses if expanded and minus icon is clicked', () => {
      const element = renderTestTemplate(defaultFooStructValue, {depth: 2});

      // Click on the '+' icon to expand element.
      browserTriggerEvent(icon(element, 'plus'), 'click');

      // Click on the '-' icon to collapse it.
      browserTriggerEvent(icon(element, 'minus'), 'click');
      // Check that fields disappeared.
      expect(element.find('grr-form-proto-single-field').length).toBe(0);

      // Check that '-' icon became '+' icon.
      expectNoIcon(element, 'minus');
      expectIcon(element, 'plus');
    });
  });

  describe('form for structure with 1 dynamic field', () => {
    let defaultFooStructValue;

    beforeEach(() => {
      defaultFooStructValue = {
        type: 'Foo',
        mro: ['Foo', 'RDFProtoStruct'],
        value: {},
      };
    });

    beforeEach(() => {
      // Reflection service is a mock. Stub out the getRDFValueDescriptor method
      // and return a promise with the reflection data.
      const data = {
        'Foo': {
          'default': {
            'type': 'Foo',
            'value': {},
          },
          'doc': 'This is a structure Foo.',
          'fields': [
            {
              'doc': 'Field 1 description.',
              'dynamic': true,
              'friendly_name': 'Field 1',
              'index': 1,
              'name': 'field_1',
              'repeated': false,
            },
          ],
          'kind': 'struct',
          'name': 'Foo',
          'mro': ['Foo', 'RDFProtoStruct'],
        },
        'PrimitiveType': {
          'default': {
            'type': 'PrimitiveType',
            'value': '',
          },
          'doc': 'Test primitive type description.',
          'kind': 'primitive',
          'name': 'PrimitiveType',
          'mro': ['PrimitiveType'],
        },
      };

      const reflectionDeferred = $q.defer();
      reflectionDeferred.resolve(data);
      spyOn(grrReflectionServiceMock, 'getRDFValueDescriptor')
          .and.callFake((type, opt_withDeps) => {
            const reflectionDeferred = $q.defer();
            reflectionDeferred.resolve(opt_withDeps ? data : data[type]);
            return reflectionDeferred.promise;
          });
    });

    it('does not prefill non-prefilled dynamic field', () => {
      const fooValue = defaultFooStructValue;
      const element = renderTestTemplate(fooValue);

      const field = element.find('grr-form-proto-repeated-field:nth(0)');
      const fieldValue = field.scope().$eval(field.attr('value'));
      expect(fieldValue).toBeUndefined();
    });

    it('uses existing dynamic field value when it\'s prefilled', () => {
      const fooValue = defaultFooStructValue;
      fooValue.value = {
        field_1: {
          type: 'PrimitiveType',
          value: '42',
        },
      };
      const element = renderTestTemplate(angular.copy(fooValue));

      const field = element.find('grr-form-proto-repeated-field:nth(0)');
      const fieldValue = field.scope().$eval(field.attr('value'));
      expect(fieldValue).toEqual(fooValue.value.field_1);
    });
  });

  describe('form for structure with 1 repeated field', () => {
    beforeEach(() => {
      // Reflection service is a mock. Stub out the getRDFValueDescriptor method
      // and return a promise with the reflection data.
      const data = {
        'Foo': {
          'default': {
            'type': 'Foo',
            'value': {},
          },
          'doc': 'This is a structure Foo.',
          'fields': [
            {
              'default': {
                'mro': ['PrimitiveType'],
                'type': 'PrimitiveType',
                'value': '',
              },
              'doc': 'Field 1 description.',
              'dynamic': false,
              'friendly_name': 'Field 1',
              'index': 1,
              'name': 'field_1',
              'repeated': true,
              'type': 'PrimitiveType',
            },
          ],
          'kind': 'struct',
          'mro': ['Foo', 'RDFProtoStruct'],
        },
        'PrimitiveType': {
          'default': {
            'type': 'PrimitiveType',
            'value': '',
          },
          'doc': 'Test primitive type description.',
          'kind': 'primitive',
          'mro': ['PrimitiveType'],
          'name': 'PrimitiveType',
        },
      };

      spyOn(grrReflectionServiceMock, 'getRDFValueDescriptor')
          .and.callFake((type, opt_withDeps) => {
            const reflectionDeferred = $q.defer();
            reflectionDeferred.resolve(opt_withDeps ? data : data[type]);
            return reflectionDeferred.promise;
          });
    });

    it('does not prefill the model', () => {
      const fooValue = {
        type: 'Foo',
        value: {},
      };
      renderTestTemplate(fooValue);

      expect(fooValue.value).toEqual({});
    });

    it('does not overwrite prefilled data', () => {
      const fooValue = {
        type: 'Foo',
        value: {
          field_1: [
            {
              type: 'PrimitiveType',
              value: '42',
            },
          ],
        },
      };
      renderTestTemplate(fooValue);
      expect(fooValue.value.field_1.length).toBe(1);
      expect(fooValue.value.field_1[0]).toEqual({
        type: 'PrimitiveType',
        value: '42',
      });
    });

    it('updates the model when repeated field is changed', () => {
      const fooValue = {
        type: 'Foo',
        value: {},
      };
      const element = renderTestTemplate(fooValue);

      const field = element.find('grr-form-proto-repeated-field:nth(0)');
      const fieldValue = field.scope().$eval(field.attr('value'));
      fieldValue.push({'type': 'PrimitiveType', value: '42'});
      $rootScope.$apply();

      expect(fooValue.value).toEqual({
        field_1: [
          {
            type: 'PrimitiveType',
            value: '42',
          },
        ],
      });
    });

    it('updates fields when repeated field is changed externally', () => {
      const fooValue = {
        type: 'Foo',
        value: {},
      };
      const element = renderTestTemplate(fooValue);

      let field = element.find('grr-form-proto-repeated-field:nth(0)');
      let fieldValue = field.scope().$eval(field.attr('value'));
      expect(fieldValue).toEqual([]);

      fooValue['value']['field_1'] = [{'type': 'PrimitiveType', value: '42'}];
      $rootScope.$apply();

      field = element.find('grr-form-proto-repeated-field:nth(0)');
      fieldValue = field.scope().$eval(field.attr('value'));
      expect(fieldValue).toEqual([{'type': 'PrimitiveType', value: '42'}]);
    });

    it('renders the repeated field with corresponding directive', () => {
      const fooValue = {
        type: 'Foo',
        value: {},
      };
      const element = renderTestTemplate(fooValue);

      // Check that grr-form-proto-repeated-field directive is used to trender
      // the repeated field.
      expect(element.find('grr-form-proto-repeated-field').length).toBe(1);
    });

    it('does not render repeated field from the hidden-fields', () => {
      const fooValue = {
        type: 'Foo',
        value: {},
      };
      const element = renderTestTemplate(fooValue, undefined, ['field_1']);

      expect(element.find('grr-form-proto-repeated-field').length).toBe(0);
    });
  });

  describe('form for union-type structure', () => {
    beforeEach(() => {
      // Reflection service is a mock. Stub out the getRDFValueDescriptor method
      // and return a promise with the reflection data.
      const data = {
        'Foo': {
          'default': {
            'type': 'Foo',
            'value': {},
          },
          'doc': 'This is a structure Foo.',
          // Non-empty union_field attribute forces GRR to treat this structure
          // as a union-type structure.
          'union_field': 'type',
          'fields': [
            {
              'default': {
                'mro': ['PrimitiveType'],
                'type': 'PrimitiveType',
                'value': '',
              },
              'doc': 'Field 1 description.',
              'dynamic': false,
              'friendly_name': 'Union Type',
              'index': 1,
              'name': 'type',
              'repeated': true,
              'type': 'PrimitiveType',
            },
          ],
          'kind': 'struct',
          'mro': ['Foo', 'RDFProtoStruct'],
        },
        'PrimitiveType': {
          'default': {
            'type': 'PrimitiveType',
            'value': '',
          },
          'doc': 'Test primitive type description.',
          'kind': 'primitive',
          'mro': ['PrimitiveType'],
          'name': 'PrimitiveType',
        },
      };

      const reflectionDeferred = $q.defer();
      reflectionDeferred.resolve(data);
      spyOn(grrReflectionServiceMock, 'getRDFValueDescriptor')
          .and.callFake((type, opt_withDeps) => {
            const reflectionDeferred = $q.defer();
            reflectionDeferred.resolve(opt_withDeps ? data : data[type]);
            return reflectionDeferred.promise;
          });
    });

    it('delegates union-type structure rendering', () => {
      const fooValue = {
        type: 'Foo',
        value: {},
      };
      const element = renderTestTemplate(fooValue);

      // Check that rendering is delegated to grr-form-proto-union.
      expect(element.find('grr-form-proto-union').length).toBe(1);
    });
  });
});


exports = {};
