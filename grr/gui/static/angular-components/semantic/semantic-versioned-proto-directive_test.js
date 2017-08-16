'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

var browserTrigger = grrUi.tests.browserTrigger;

describe('semantic versioned proto directive', function() {
  var $q, $compile, $rootScope, grrReflectionService;

  beforeEach(module('/static/angular-components/semantic/' +
      'semantic-versioned-proto.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrReflectionService = $injector.get('grrReflectionService');

    var deferred = $q.defer();
    deferred.resolve({
      'TheType': {
        kind: 'struct',
        fields: [
          {
            name: 'field',
            type: 'TheType'
          },
          {
            name: 'foo',
            type: 'RDFString'
          }
        ],
        default: {}
      },
      'RDFString': {
        kind: 'primitive',
        default: ''
      }
    });
    grrReflectionService.getRDFValueDescriptor = jasmine.createSpy(
        'getRDFValueDescriptor').and.returnValue(deferred.promise);
  }));

  var renderTestTemplate = function(value, callback, depth) {
    $rootScope.value = value;
    $rootScope.callback = callback;
    $rootScope.depth = depth;

    var template = '<grr-semantic-versioned-proto ' +
        'value="value" history-depth="depth" ' +
        'on-field-click="callback(fieldPath)" />';

    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  var oneLevelValue = {
    type: 'TheType',
    value: {
      foo: {
        type: 'RDFString',
        value: 'blah'
      }
    }
  };

  var twoLevelValue = {
    type: 'TheType',
    value: {
      field: {
        type: 'TheType',
        value: {
          foo: {
            type: 'RDFString',
            value: 'bar'
          }
        }
      },
      foo: {
        type: 'RDFString',
        value: 'blah'
      }
    }
  };

  it('adds history button to 1st-level field', function() {
    var element = renderTestTemplate(oneLevelValue, function() {}, 1);
    expect(element.find('td.proto_history button').length).toBe(1);
  });

  it('passes a correct field path for a 1st-level field', function() {
    var callback = jasmine.createSpy();
    var element = renderTestTemplate(oneLevelValue, callback, 1);
    browserTrigger(element.find('td.proto_history button'), 'click');

    expect(callback.calls.count()).toBe(1);
    expect(callback.calls.first().args).toEqual(['foo']);
  });

  it('adds history button to 2nd-level field', function() {
    var element = renderTestTemplate(twoLevelValue, function() {}, 2);
    expect(element.find('td.proto_value td.proto_history button').length).toBe(1);
  });


  it('passes a correct field path for a 2nd-level field', function() {
    var callback = jasmine.createSpy();
    var element = renderTestTemplate(twoLevelValue, callback, 2);
    browserTrigger(element.find('td.proto_value td.proto_history button'), 'click');

    expect(callback.calls.count()).toBe(1);
    expect(callback.calls.first().args).toEqual(['field.foo']);
  });

  it('does not add history button outside history-depth', function() {
    var element = renderTestTemplate(twoLevelValue, function() {}, 1);
    expect(element.find('td.proto_value td.proto_history button').length).toBe(0);
  });
});
