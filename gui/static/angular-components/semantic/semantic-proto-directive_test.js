'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

goog.scope(function() {

describe('semantic proto directive', function() {
  var $compile, $rootScope, $q, grrReflectionService;

  beforeEach(module('/static/angular-components/semantic/semantic-proto.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

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

  it('does not show anything when value is empty', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('');
  });

  it('respects fields order', function() {
    var element = renderTestTemplate({
      type: 'RDFProtoStruct',
      value: {
        client_id: 'client_id',
        system_info: 'system_info',
        client_info: 'client_info'
      }
    }, {
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
        client_id: 'client_id',
        system_info: 'system_info',
        client_info: 'client_info'
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

});  // goog.scope
