'use strict';

goog.module('grrUi.semantic.semanticVersionedProtoDirectiveTest');

const {browserTriggerEvent, stubDirective, testsModule} = goog.require('grrUi.tests');
const {semanticModule} = goog.require('grrUi.semantic.semantic');


describe('semantic versioned proto directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrReflectionService;


  beforeEach(module('/static/angular-components/semantic/' +
      'semantic-versioned-proto.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrReflectionService = $injector.get('grrReflectionService');

    const deferred = $q.defer();
    deferred.resolve({
      'TheType': {
        kind: 'struct',
        fields: [
          {
            name: 'field',
            type: 'TheType',
          },
          {
            name: 'foo',
            type: 'RDFString',
          },
        ],
        default: {},
      },
      'RDFString': {
        kind: 'primitive',
        default: '',
      },
    });
    grrReflectionService.getRDFValueDescriptor = jasmine.createSpy(
        'getRDFValueDescriptor').and.returnValue(deferred.promise);
  }));

  const renderTestTemplate = (value, callback, depth) => {
    $rootScope.value = value;
    $rootScope.callback = callback;
    $rootScope.depth = depth;

    const template = '<grr-semantic-versioned-proto ' +
        'value="value" history-depth="depth" ' +
        'on-field-click="callback(fieldPath)" />';

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const oneLevelValue = {
    type: 'TheType',
    value: {
      foo: {
        type: 'RDFString',
        value: 'blah',
      },
    },
  };

  const twoLevelValue = {
    type: 'TheType',
    value: {
      field: {
        type: 'TheType',
        value: {
          foo: {
            type: 'RDFString',
            value: 'bar',
          },
        },
      },
      foo: {
        type: 'RDFString',
        value: 'blah',
      },
    },
  };

  it('renders only after the "value" binding is set', () => {
    const element = renderTestTemplate(undefined, () => {}, 1);
    expect(element.find('.proto_history button').length).toBe(0);

    $rootScope.value = oneLevelValue;
    $rootScope.$apply();
    expect(element.find('.proto_history button').length).toBe(1);
  });

  it('"value" binding is effectively a one-time binding', () => {
    const element = renderTestTemplate(oneLevelValue, () => {}, 1);
    expect(element.find('.proto_history button').length).toBe(1);

    const newValue = angular.copy(oneLevelValue);
    newValue['value'] = {};
    $rootScope.value = newValue;
    $rootScope.$apply();
    expect(element.find('.proto_history button').length).toBe(1);
  });

  it('adds history button to 1st-level field', () => {
    const element = renderTestTemplate(oneLevelValue, () => {}, 1);
    expect(element.find('.proto_history button').length).toBe(1);
  });

  it('passes a correct field path for a 1st-level field', () => {
    const callback = jasmine.createSpy();
    const element = renderTestTemplate(oneLevelValue, callback, 1);
    browserTriggerEvent(element.find('.proto_history button'), 'click');

    expect(callback.calls.count()).toBe(1);
    expect(callback.calls.first().args).toEqual(['foo']);
  });

  it('adds history button to 2nd-level field', () => {
    const element = renderTestTemplate(twoLevelValue, () => {}, 2);
    expect(element.find('td.proto_value .proto_history button').length).toBe(1);
  });


  it('passes a correct field path for a 2nd-level field', () => {
    const callback = jasmine.createSpy();
    const element = renderTestTemplate(twoLevelValue, callback, 2);
    browserTriggerEvent(element.find('td.proto_value .proto_history button'), 'click');

    expect(callback.calls.count()).toBe(1);
    expect(callback.calls.first().args).toEqual(['field.foo']);
  });

  it('does not add history button outside history-depth', () => {
    const element = renderTestTemplate(twoLevelValue, () => {}, 1);
    expect(element.find('td.proto_value .proto_history button').length).toBe(0);
  });
});


exports = {};
