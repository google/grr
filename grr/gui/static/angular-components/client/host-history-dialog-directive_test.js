'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

var browserTrigger = grrUi.tests.browserTrigger;

describe('semantic versioned proto directive', function() {
  var $q, $compile, $rootScope, grrApiService, grrTimeService;

  beforeEach(module('/static/angular-components/client/' +
      'host-history-dialog.html'));
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
    grrTimeService = $injector.get('grrTimeService');
  }));

  var renderTestTemplate = function(fieldPath) {
    $rootScope.clientId = 'C.00000000000000001';
    $rootScope.fieldPath = fieldPath;
    $rootScope.close = function() {};

    var template = '<grr-host-history-dialog ' +
        'client-id="clientId" field-path="fieldPath" ' +
        'close="close()" />';

    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('fetches data for the last year', function() {
    // One year + 1 millisecond.
    spyOn(grrTimeService, 'getCurrentTimeMs').and.returnValue(31536000001);
    spyOn(grrApiService, 'get').and.returnValue($q.defer().promise);

    renderTestTemplate('foo');
    expect(grrApiService.get).toHaveBeenCalledWith(
        '/clients/C.00000000000000001/versions',
        {
          mode: 'DIFF',
          start: 1000,
          end: 31536000001000
        });
  });

  it('correctly shows data for field path with 1 component', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
    deferred.resolve({
      data: {
        items: [
          {
            type: 'Foo',
            value: {
              field: {
                type: 'RDFString',
                value: 'bar1'
              },
              age: {
                type: 'RDFDatetime',
                value: 1
              }
            }
          },
          {
            type: 'Foo',
            value: {
              age: {
                type: 'RDFDatetime',
                value: 2
              }
            }
          },
          {
            type: 'Foo',
            value: {
              field: {
                type: 'RDFString',
                value: 'bar2'
              },
              age: {
                type: 'RDFDatetime',
                value: 3
              }
            }
          }
        ]
      }
    });

    var element = renderTestTemplate('field');
    // 2nd item shouldn't be shown since it doesn't have the needed field.
    expect(element.find('td.version grr-semantic-value').length).toBe(2);

    // Values should be listed in their timestamps order (with timtestamps
    // descending).
    var directive = element.find('td.version:nth(0) grr-semantic-value');
    var value = directive.scope().$eval(directive.attr('value'));
    expect(value).toEqual({type: 'RDFString', value: 'bar2'});

    var directive = element.find('td.version:nth(1) grr-semantic-value');
    var value = directive.scope().$eval(directive.attr('value'));
    expect(value).toEqual({type: 'RDFString', value: 'bar1'});
  });

  it('correctly shows data for field path with 2 components', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
    deferred.resolve({
      data: {
        items: [
          {
            type: 'Foo',
            value: {
              field1: {
                type: 'Bar',
                value: {
                  field2: {
                    type: 'RDFString',
                    value: 'oh1'
                  }
                }
              },
              age: {
                type: 'RDFDatetime',
                value: 1
              }
            }
          },
          {
            type: 'Foo',
            value: {
              age: {
                type: 'RDFDatetime',
                value: 2
              }
            }
          },
          {
            type: 'Foo',
            value: {
              field1: {
                type: 'Bar',
                value: {
                  field2: {
                    type: 'RDFString',
                    value: 'oh2'
                  }
                }
              },
              age: {
                type: 'RDFDatetime',
                value: 3
              }
            }
          }
        ]
      }
    });

    var element = renderTestTemplate('field1.field2');
    // 2nd item shouldn't be shown since it doesn't have the needed field.
    expect(element.find('td.version grr-semantic-value').length).toBe(2);

    // Values should be listed in their timestamps order (with timtestamps
    // descending).
    var directive = element.find('td.version:nth(0) grr-semantic-value');
    var value = directive.scope().$eval(directive.attr('value'));
    expect(value).toEqual({type: 'RDFString', value: 'oh2'});

    var directive = element.find('td.version:nth(1) grr-semantic-value');
    var value = directive.scope().$eval(directive.attr('value'));
    expect(value).toEqual({type: 'RDFString', value: 'oh1'});
  });
});
