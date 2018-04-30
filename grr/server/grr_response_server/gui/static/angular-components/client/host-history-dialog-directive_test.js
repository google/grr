'use strict';

goog.module('grrUi.client.hostHistoryDialogDirectiveTest');

const {clientModule} = goog.require('grrUi.client.client');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('semantic versioned proto directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;
  let grrTimeService;


  beforeEach(module('/static/angular-components/client/' +
      'host-history-dialog.html'));
  beforeEach(module(clientModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
    grrTimeService = $injector.get('grrTimeService');
  }));

  const renderTestTemplate = (fieldPath) => {
    $rootScope.clientId = 'C.00000000000000001';
    $rootScope.fieldPath = fieldPath;
    $rootScope.close = (() => {});

    const template = '<grr-host-history-dialog ' +
        'client-id="clientId" field-path="fieldPath" ' +
        'close="close()" />';

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('fetches data for the last year', () => {
    // One year + 1 millisecond.
    spyOn(grrTimeService, 'getCurrentTimeMs').and.returnValue(31536000001);
    spyOn(grrApiService, 'get').and.returnValue($q.defer().promise);

    renderTestTemplate('foo');
    expect(grrApiService.get)
        .toHaveBeenCalledWith('/clients/C.00000000000000001/versions', {
          mode: 'DIFF',
          start: 1000,
          end: 31536000001000,
        });
  });

  it('correctly shows data for field path with 1 component', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
    deferred.resolve({
      data: {
        items: [
          {
            type: 'Foo',
            value: {
              field: {
                type: 'RDFString',
                value: 'bar1',
              },
              age: {
                type: 'RDFDatetime',
                value: 1,
              },
            },
          },
          {
            type: 'Foo',
            value: {
              age: {
                type: 'RDFDatetime',
                value: 2,
              },
            },
          },
          {
            type: 'Foo',
            value: {
              field: {
                type: 'RDFString',
                value: 'bar2',
              },
              age: {
                type: 'RDFDatetime',
                value: 3,
              },
            },
          },
        ],
      },
    });

    const element = renderTestTemplate('field');
    // 2nd item shouldn't be shown since it doesn't have the needed field.
    expect(element.find('td.version grr-semantic-value').length).toBe(2);

    // Values should be listed in their timestamps order (with timtestamps
    // descending).
    let directive = element.find('td.version:nth(0) grr-semantic-value');
    let value = directive.scope().$eval(directive.attr('value'));
    expect(value).toEqual({type: 'RDFString', value: 'bar2'});

    directive = element.find('td.version:nth(1) grr-semantic-value');
    value = directive.scope().$eval(directive.attr('value'));
    expect(value).toEqual({type: 'RDFString', value: 'bar1'});
  });

  it('correctly shows data for field path with 2 components', () => {
    const deferred = $q.defer();
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
                    value: 'oh1',
                  },
                },
              },
              age: {
                type: 'RDFDatetime',
                value: 1,
              },
            },
          },
          {
            type: 'Foo',
            value: {
              age: {
                type: 'RDFDatetime',
                value: 2,
              },
            },
          },
          {
            type: 'Foo',
            value: {
              field1: {
                type: 'Bar',
                value: {
                  field2: {
                    type: 'RDFString',
                    value: 'oh2',
                  },
                },
              },
              age: {
                type: 'RDFDatetime',
                value: 3,
              },
            },
          },
        ],
      },
    });

    const element = renderTestTemplate('field1.field2');
    // 2nd item shouldn't be shown since it doesn't have the needed field.
    expect(element.find('td.version grr-semantic-value').length).toBe(2);

    // Values should be listed in their timestamps order (with timtestamps
    // descending).
    let directive = element.find('td.version:nth(0) grr-semantic-value');
    let value = directive.scope().$eval(directive.attr('value'));
    expect(value).toEqual({type: 'RDFString', value: 'oh2'});

    directive = element.find('td.version:nth(1) grr-semantic-value');
    value = directive.scope().$eval(directive.attr('value'));
    expect(value).toEqual({type: 'RDFString', value: 'oh1'});
  });
});


exports = {};
