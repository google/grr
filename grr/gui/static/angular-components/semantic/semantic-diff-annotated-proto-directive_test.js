'use strict';

goog.module('grrUi.semantic.semanticDiffAnnotatedProtoDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-semantic-diff-annotated-proto directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrReflectionService;


  beforeEach(module('/static/angular-components/semantic/semantic-diff-annotated-proto.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');

    grrReflectionService = $injector.get('grrReflectionService');
    spyOn(grrReflectionService, 'getRDFValueDescriptor');

    const descriptors = {
      'Bar': {},
      'Foo': {
        fields: [
          {name: 'a'},
          {name: 'foo'},
          {name: 'bar'},
        ],
      },
    };
    grrReflectionService.getRDFValueDescriptor.and.callFake((typeName) => {
      const deferred = $q.defer();
      deferred.resolve(descriptors[typeName]);
      return deferred.promise;
    });
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-semantic-diff-annotated-proto value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('renders only after the "value" binding is set', () => {
    const element = renderTestTemplate(undefined);
    expect(element.find('td:contains("foo")').length).toBe(0);

    $rootScope.value = {
      type: 'Foo',
      value: {
        foo: {
          type: 'Bar',
          value: 42,
        },
      },
    };
    $rootScope.$apply();

    expect(element.find('td:contains("foo")').length).toBe(1);
  });

  it('"value" binding is effectively a one-time binding', () => {
    const value = {
      type: 'Foo',
      value: {
        foo: {
          type: 'Bar',
          value: 42,
        },
      },
    };
    const element = renderTestTemplate(value);
    expect(element.find('td:contains("bar")').length).toBe(0);

    const newValue = angular.copy(value);
    newValue['value']['bar'] = {
      type: 'Bar',
      value: 43,
    };
    $rootScope.value = newValue;
    $rootScope.$apply();

    expect(element.find('td:contains("bar")').length).toBe(0);
  });

  angular.forEach(['added', 'changed', 'removed'], (annotation) => {
    it(`renders "${annotation}" annotation on the value itself correctly`,
       () => {
         const value = {
           type: 'Foo',
           value: 42,
           _diff: annotation,
         };

         const element = renderTestTemplate(value);
         expect(element.find(`table.diff-${annotation}`).length).toBe(1);
       });

    it(`renders "${annotation}"-annotated non-repeated field correctly`, () => {
      const value = {
        type: 'Foo',
        value: {
          a: {
            type: 'Bar',
            value: 42,
            _diff: annotation,
          },
        },
      };

      const element = renderTestTemplate(value);
      expect(element.find(`tr.diff-${annotation}`).length).toBe(1);
    });

    it(`renders "${annotation}"-annotated repeated field correctly`, () => {
      const value = {
        type: 'Foo',
        value: {
          a: [
            {
              type: 'Bar',
              value: 42,
              _diff: annotation,
            },
          ],
        },
      };

      const element = renderTestTemplate(value);
      expect(element.find(`div.repeated.diff-${annotation}`).length).toBe(1);
    });
  });
});


exports = {};
