'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.semantic.semanticProtoDirective.buildItems');
goog.require('grrUi.semantic.semanticProtoDirective.buildUnionItems');
goog.require('grrUi.semantic.semanticProtoDirective.getUnionFieldValue');
goog.require('grrUi.tests.module');

goog.scope(function() {

describe('semantic proto directive', function() {

  describe('getUnionFieldValue()', function() {
    var getUnionFieldValue =
        grrUi.semantic.semanticProtoDirective.getUnionFieldValue;

    it('throws if descriptor doesn\'t have union_field', function() {
      expect(function() {
        getUnionFieldValue({}, {});
      }).toThrow();
    });

    it('returns union field value when it\'s set', function() {
      var value = {
        type: 'FooType',
        value: {
          action_type: {
            type: 'unicode',
            value: 'DOWNLOAD'
          }
        }
      };
      var descriptor = {
        union_field: 'action_type'
      };
      expect(getUnionFieldValue(value, descriptor)).toBe('download');
    });

    it('returns union field value default if it\'s not set', function() {
      var value = {
        type: 'FooType',
        value: {}
      };
      var descriptor = {
        union_field: 'action_type',
        fields: [
          {
            name: 'action_type',
            default: {
              type: 'unicode',
              value: 'DOWNLOAD'
            }
          }
        ]
      };
      expect(getUnionFieldValue(value, descriptor)).toBe('download');
    });
  });

  describe('buildUnionItems()', function() {
    var buildUnionItems = grrUi.semantic.semanticProtoDirective.buildUnionItems;

    var descriptor = {
      union_field: 'action_type',
      fields: [
        {
          name: 'action_type',
          default: {
            type: 'unicode',
            value: 'SEND_TO_SOCKET'
          }
        },
        {
          name: 'download',
          default: {
            type: 'unicode',
            value: 'defaultFoo'
          }
        },
        {
          name: 'send_to_socket',
          default: {
            type: 'unicode',
            value: 'defaultBar'
          }
        }
      ]
    };

    var valueWithSetFields = {
      type: 'FooType',
      value: {
        action_type: {
          type: 'unicode',
          value: 'DOWNLOAD'
        },
        download: {
          type: 'unicode',
          value: 'foo'
        },
        send_to_socket: {
          type: 'unicode',
          value: 'bar'
        }
      }
    };

    var valueWithUnsetFields = {
      type: 'FooType',
      value: {}
    };

    it('excludes fields not pointed by set union field value', function() {
      var items = buildUnionItems(valueWithSetFields, descriptor);
      for (var i = 0; i < items.length; ++i) {
        expect(items[i].key).not.toBe('send_to_socket');
      }
    });

    it('excludes fields not pointed by default union field value', function() {
      var items = buildUnionItems(valueWithUnsetFields, descriptor);
      for (var i = 0; i < items.length; ++i) {
        expect(items[i].key).not.toBe('download');
      }
    });

    it('includes union field when it\'s set', function() {
      var items = buildUnionItems(valueWithSetFields, descriptor);
      expect(items[0]['key']).toBe('action_type');
      expect(items[0]['value']['value']).toBe('DOWNLOAD');
    });

    it('includes union field value when it\'s set', function() {
      var items = buildUnionItems(valueWithSetFields, descriptor);
      expect(items[1]['key']).toBe('download');
      expect(items[1]['value']['value']).toBe('foo');
    });

    it('includes union field default when it\'s not set', function() {
      var items = buildUnionItems(valueWithUnsetFields, descriptor);
      expect(items[0]['key']).toBe('action_type');
      expect(items[0]['value']['value']).toBe('SEND_TO_SOCKET');
    });

    it('includes union field value default when it\'s not set', function() {
      var items = buildUnionItems(valueWithUnsetFields, descriptor);
      expect(items[1]['key']).toBe('send_to_socket');
      expect(items[1]['value']['value']).toBe('defaultBar');
    });
  });

  describe('buildItems()', function() {
    var buildItems = grrUi.semantic.semanticProtoDirective.buildItems;

    var descriptor = {
      fields: [
        {
          name: 'foo',
          default: {
            type: 'unicode',
            value: 'defaultFoo'
          }
        },
        {
          name: 'bar',
          default: {
            type: 'unicode',
            value: 'defaultBar'
          }
        }
      ]
    };

    var value = {
      type: 'Struct',
      value: {
        foo: {
          type: 'unicode',
          value: 'theFoo'
        }
      }
    };

    it('includes set fields only', function() {
      var items = buildItems(value, descriptor);
      expect(items.length).toBe(1);
      expect(items[0]['key']).toBe('foo');
      expect(items[0]['value']['value']).toBe('theFoo');
    });
  });

  var $compile, $rootScope, $q, grrReflectionService;

  beforeEach(module('/static/angular-components/semantic/semantic-proto.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    spyOn(grrReflectionService, 'getRDFValueDescriptor');
  }));

  var renderTestTemplate = function(value, descriptors) {
    $rootScope.value = value;

    if (descriptors) {
      grrReflectionService.getRDFValueDescriptor.and.callFake(
          function(typeName) {
            var deferred = $q.defer();
            deferred.resolve(descriptors[typeName]);
            return deferred.promise;
          });
    }

    var template = '<grr-semantic-proto value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  describe('with non-union-type value', function() {
    it('does not show anything when value is empty', function() {
      var element = renderTestTemplate(null);
      expect(element.text().trim()).toBe('');
    });

    it('respects fields order', function() {
      var element = renderTestTemplate({
        type: 'RDFProtoStruct',
        value: {
          client_id: {
            type: 'unicode',
            value: 'client_id'
          },
          system_info: {
            type: 'unicode',
            value: 'system_info',
          },
          client_info: {
            type: 'unicode',
            value: 'client_info'
          }
        }
      }, {
        'unicode': {
        },
        'RDFProtoStruct': {
          fields: [
            {
              name: 'client_id'
            },
            {
              name: 'system_info'
            },
            {
              name: 'client_info'
            }
          ]
        }
      });
      expect($('tr:nth(0)', element).text()).toContain('client_id');
      expect($('tr:nth(1)', element).text()).toContain('system_info');
      expect($('tr:nth(2)', element).text()).toContain('client_info');

      element = renderTestTemplate({
        type: 'RDFProtoStruct',
        value: {
          client_id: {
            type: 'unicode',
            value: 'client_id'
          },
          system_info: {
            type: 'unicode',
            value: 'system_info'
          },
          client_info: {
            type: 'unicode',
            value: 'client_info'
          }
        }
      }, {
        'RDFProtoStruct': {
          fields: [
            {
              name: 'client_info'
            },
            {
              name: 'system_info'
            },
            {
              name: 'client_id'
            }
          ]
        }
      });
      expect($('tr:nth(0)', element).text()).toContain('client_info');
      expect($('tr:nth(1)', element).text()).toContain('system_info');
      expect($('tr:nth(2)', element).text()).toContain('client_id');
    });
  });

  describe('with union-type values', function() {
    var valueWithSetValues = {
      type: 'RDFProtoStruct',
      value: {
        action_type: {
          type: 'unicode',
          value: 'SEND_TO_SOCKET'
        },
        download: {
          type: 'unicode',
          value: 'foo'
        },
        send_to_socket: {
          type: 'unicode',
          value: 'bar'
        }
      }
    };

    var valueWithUnsetValues = {
      type: 'RDFProtoStruct',
      value: {}
    };

    var descriptors = {
        'unicode': {
        },
        'RDFProtoStruct': {
          union_field: 'action_type',
          fields: [
            {
              name: 'action_type',
              default: {
                type: 'unicode',
                value: 'DOWNLOAD'
              }
            },
            {
              name: 'download',
              default: {
                type: 'unicode',
                value: 'foo'
              }
            },
            {
              name: 'send_to_socket',
              default: {
                type: 'unicode',
                value: 'bar'
              }
            }
          ]
        }
    };

    it('doesn\'t show inactive union fields', function() {
      var element = renderTestTemplate(valueWithSetValues, descriptors);
      expect($('tr', element).length).toBe(2);
      expect($('tr:nth(0)', element).text()).not.toContain('download');
      expect($('tr:nth(1)', element).text()).not.toContain('download');
    });

    it('shows action type when explicitly set', function() {
      var element = renderTestTemplate(valueWithSetValues, descriptors);
      expect($('tr:nth(0)', element).text()).toContain('action_type');
    });

    it('shows active union field when explicitly set', function() {
      var element = renderTestTemplate(valueWithSetValues, descriptors);
      expect($('tr:nth(1)', element).text()).toContain('send_to_socket');
    });

    it('shows action type when not explicitly set', function() {
      var element = renderTestTemplate(valueWithUnsetValues, descriptors);
      expect($('tr:nth(0)', element).text()).toContain('action_type');
    });

    it('shows active union field when not explicitly set', function() {
      var element = renderTestTemplate(valueWithUnsetValues, descriptors);
      expect($('tr:nth(1)', element).text()).toContain('download');
    });
  });
});

});  // goog.scope
