'use strict';

goog.module('grrUi.semantic.semanticProtoDirectiveTest');

const {buildItems, buildNonUnionItems, buildUnionItems, getUnionFieldValue} = goog.require('grrUi.semantic.semanticProtoDirective');
const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('semantic proto directive', () => {
  describe('getUnionFieldValue()', () => {

    it('throws if descriptor doesn\'t have union_field', () => {
      expect(() => {
        getUnionFieldValue({}, {});
      }).toThrow();
    });

    it('returns union field value when it\'s set', () => {
      const value = {
        type: 'FooType',
        value: {
          action_type: {
            type: 'unicode',
            value: 'DOWNLOAD',
          },
        },
      };
      const descriptor = {
        union_field: 'action_type',
      };
      expect(getUnionFieldValue(value, descriptor)).toBe('download');
    });

    it('returns union field value default if it\'s not set', () => {
      const value = {
        type: 'FooType',
        value: {},
      };
      const descriptor = {
        union_field: 'action_type',
        fields: [
          {
            name: 'action_type',
            default: {
              type: 'unicode',
              value: 'DOWNLOAD',
            },
          },
        ],
      };
      expect(getUnionFieldValue(value, descriptor)).toBe('download');
    });
  });

  describe('buildUnionItems()', () => {

    const descriptor = {
      union_field: 'action_type',
      fields: [
        {
          name: 'action_type',
          default: {
            type: 'unicode',
            value: 'SEND_TO_SOCKET',
          },
        },
        {
          name: 'download',
          default: {
            type: 'unicode',
            value: 'defaultFoo',
          },
        },
        {
          name: 'send_to_socket',
          default: {
            type: 'unicode',
            value: 'defaultBar',
          },
        },
      ],
    };

    const valueWithSetFields = {
      type: 'FooType',
      value: {
        action_type: {
          type: 'unicode',
          value: 'DOWNLOAD',
        },
        download: {
          type: 'unicode',
          value: 'foo',
        },
        send_to_socket: {
          type: 'unicode',
          value: 'bar',
        },
      },
    };

    const valueWithUnsetFields = {
      type: 'FooType',
      value: {},
    };

    it('excludes fields not pointed by set union field value', () => {
      const items = buildUnionItems(valueWithSetFields, descriptor);
      for (let i = 0; i < items.length; ++i) {
        expect(items[i].key).not.toBe('send_to_socket');
      }
    });

    it('excludes fields not pointed by default union field value', () => {
      const items = buildUnionItems(valueWithUnsetFields, descriptor);
      for (let i = 0; i < items.length; ++i) {
        expect(items[i].key).not.toBe('download');
      }
    });

    it('includes union field when it\'s set', () => {
      const items = buildUnionItems(valueWithSetFields, descriptor);
      expect(items[0]['key']).toBe('action_type');
      expect(items[0]['value']['value']).toBe('DOWNLOAD');
    });

    it('includes union field value when it\'s set', () => {
      const items = buildUnionItems(valueWithSetFields, descriptor);
      expect(items[1]['key']).toBe('download');
      expect(items[1]['value']['value']).toBe('foo');
    });

    it('includes union field default when it\'s not set', () => {
      const items = buildUnionItems(valueWithUnsetFields, descriptor);
      expect(items[0]['key']).toBe('action_type');
      expect(items[0]['value']['value']).toBe('SEND_TO_SOCKET');
    });

    it('includes union field value default when it\'s not set', () => {
      const items = buildUnionItems(valueWithUnsetFields, descriptor);
      expect(items[1]['key']).toBe('send_to_socket');
      expect(items[1]['value']['value']).toBe('defaultBar');
    });
  });

  describe('buildNonUnionItems()', () => {

    const descriptor = {
      fields: [
        {
          name: 'foo',
          default: {
            type: 'unicode',
            value: 'defaultFoo',
          },
        },
        {
          name: 'bar',
          default: {
            type: 'unicode',
            value: 'defaultBar',
          },
        },
      ],
    };

    const value = {
      type: 'Struct',
      value: {
        foo: {
          type: 'unicode',
          value: 'theFoo',
        },
      },
    };

    it('includes set fields only', () => {
      const items = buildNonUnionItems(value, descriptor);
      expect(items.length).toBe(1);
      expect(items[0]['key']).toBe('foo');
      expect(items[0]['value']['value']).toBe('theFoo');
    });
  });

  describe('buildItems()', () => {

    it('builds items for a non-union-type value', () => {
      const descriptor = {
        fields: [
          {
            name: 'foo',
          },
        ],
      };

      const value = {
        type: 'Struct',
        value: {
          foo: {
            type: 'unicode',
            value: 'theFoo',
          },
        },
      };

      const items = buildItems(value, descriptor);
      expect(items.length).toBe(1);
      expect(items[0]['key']).toBe('foo');
      expect(items[0]['value']['value']).toBe('theFoo');
    });

    it('builds items for a union-type value', () => {
      const descriptor = {
        union_field: 'action_type',
        fields: [
          {
            name: 'action_type',
          },
          {
            name: 'send_to_socket',
          },
        ],
      };


      const valueWithSetFields = {
        type: 'FooType',
        value: {
          action_type: {
            type: 'unicode',
            value: 'SEND_TO_SOCKET',
          },
          send_to_socket: {
            type: 'unicode',
            value: 'bar',
          },
        },
      };

      const items = buildItems(valueWithSetFields, descriptor);
      expect(items[0]['key']).toBe('action_type');
      expect(items[0]['value']['value']).toBe('SEND_TO_SOCKET');
      expect(items[1]['key']).toBe('send_to_socket');
      expect(items[1]['value']['value']).toBe('bar');
    });
  });


  let $compile;
  let $q;
  let $rootScope;
  let grrReflectionService;


  beforeEach(module('/static/angular-components/semantic/semantic-proto.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    spyOn(grrReflectionService, 'getRDFValueDescriptor');
  }));

  const renderTestTemplate = (value, descriptors) => {
    $rootScope.value = value;

    if (descriptors) {
      grrReflectionService.getRDFValueDescriptor.and.callFake((typeName) => {
        const deferred = $q.defer();
        deferred.resolve(descriptors[typeName]);
        return deferred.promise;
      });
    }

    const template = '<grr-semantic-proto value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('renders only after the "value" binding is set', () => {
    const element = renderTestTemplate(undefined, {
      'Struct': {
        fields: [
          {
            name: 'foo',
          },
        ],
      },
    });

    expect(element.find('td:contains("foo")').length).toBe(0);

    $rootScope.value = {
      type: 'Struct',
      value: {
        foo: {
          type: 'unicode',
          value: 'theFoo',
        },
      },
    };
    $rootScope.$apply();
    expect(element.find('td:contains("foo")').length).toBe(1);
  });

  it('"value" binding is effectively a one-time binding', () => {
    const value = {
      type: 'Struct',
      value: {
        foo: {
          type: 'unicode',
          value: 'theFoo',
        },
      },
    };
    const element = renderTestTemplate(value, {
      'Struct': {
        fields: [
          {
            name: 'foo',
            name: 'bar',
          },
        ],
      },
    });
    expect(element.find('td:contains("bar")').length).toBe(0);
    const newValue = angular.copy(value);
    newValue['value']['bar'] = {
      type: 'unicode',
      value: 'theBar',
    };
    $rootScope.value = newValue;
    $rootScope.$apply();
    expect(element.find('td:contains("bar")').length).toBe(0);
  });

  describe('with non-union-type value', () => {
    it('does not show anything when value is empty', () => {
      const element = renderTestTemplate(null);
      expect(element.text().trim()).toBe('');
    });

    it('respects fields order', () => {
      let element = renderTestTemplate(
          {
            type: 'RDFProtoStruct',
            value: {
              client_id: {
                type: 'unicode',
                value: 'client_id',
              },
              system_info: {
                type: 'unicode',
                value: 'system_info',
              },
              client_info: {
                type: 'unicode',
                value: 'client_info',
              },
            },
          },
          {
            'unicode': {},
            'RDFProtoStruct': {
              fields: [
                {
                  name: 'client_id',
                },
                {
                  name: 'system_info',
                },
                {
                  name: 'client_info',
                },
              ],
            },
          });
      expect($('tr:nth(0)', element).text()).toContain('client_id');
      expect($('tr:nth(1)', element).text()).toContain('system_info');
      expect($('tr:nth(2)', element).text()).toContain('client_info');

      element = renderTestTemplate(
          {
            type: 'RDFProtoStruct',
            value: {
              client_id: {
                type: 'unicode',
                value: 'client_id',
              },
              system_info: {
                type: 'unicode',
                value: 'system_info',
              },
              client_info: {
                type: 'unicode',
                value: 'client_info',
              },
            },
          },
          {
            'RDFProtoStruct': {
              fields: [
                {
                  name: 'client_info',
                },
                {
                  name: 'system_info',
                },
                {
                  name: 'client_id',
                },
              ],
            },
          });
      expect($('tr:nth(0)', element).text()).toContain('client_info');
      expect($('tr:nth(1)', element).text()).toContain('system_info');
      expect($('tr:nth(2)', element).text()).toContain('client_id');
    });
  });

  describe('with union-type values', () => {
    const valueWithSetValues = {
      type: 'RDFProtoStruct',
      value: {
        action_type: {
          type: 'unicode',
          value: 'SEND_TO_SOCKET',
        },
        download: {
          type: 'unicode',
          value: 'foo',
        },
        send_to_socket: {
          type: 'unicode',
          value: 'bar',
        },
      },
    };

    const valueWithUnsetValues = {
      type: 'RDFProtoStruct',
      value: {},
    };

    const descriptors = {
      'unicode': {},
      'RDFProtoStruct': {
        union_field: 'action_type',
        fields: [
          {
            name: 'action_type',
            default: {
              type: 'unicode',
              value: 'DOWNLOAD',
            },
          },
          {
            name: 'download',
            default: {
              type: 'unicode',
              value: 'foo',
            },
          },
          {
            name: 'send_to_socket',
            default: {
              type: 'unicode',
              value: 'bar',
            },
          },
        ],
      },
    };

    it('doesn\'t show inactive union fields', () => {
      const element = renderTestTemplate(valueWithSetValues, descriptors);
      expect($('tr', element).length).toBe(2);
      expect($('tr:nth(0)', element).text()).not.toContain('download');
      expect($('tr:nth(1)', element).text()).not.toContain('download');
    });

    it('shows action type when explicitly set', () => {
      const element = renderTestTemplate(valueWithSetValues, descriptors);
      expect($('tr:nth(0)', element).text()).toContain('action_type');
    });

    it('shows active union field when explicitly set', () => {
      const element = renderTestTemplate(valueWithSetValues, descriptors);
      expect($('tr:nth(1)', element).text()).toContain('send_to_socket');
    });

    it('shows action type when not explicitly set', () => {
      const element = renderTestTemplate(valueWithUnsetValues, descriptors);
      expect($('tr:nth(0)', element).text()).toContain('action_type');
    });

    it('shows active union field when not explicitly set', () => {
      const element = renderTestTemplate(valueWithUnsetValues, descriptors);
      expect($('tr:nth(1)', element).text()).toContain('download');
    });
  });
});


exports = {};
