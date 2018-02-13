'use strict';

goog.module('grrUi.core.reflectionServiceTest');

const {ReflectionService} = goog.require('grrUi.core.reflectionService');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('AFF4 items provider directive', () => {
  let $q;
  let $rootScope;
  let grrApiServiceMock;
  let grrReflectionService;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');

    grrApiServiceMock = {get: function() {}};
    grrReflectionService = $injector.instantiate(ReflectionService, {
      'grrApiService': grrApiServiceMock,
    });
  }));

  it('fetches data from the server only once', () => {
    const deferred = $q.defer();
    spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

    grrReflectionService.getRDFValueDescriptor('Duration');
    grrReflectionService.getRDFValueDescriptor('RDFDatetime');
    // Check that only 1 call to API service was made.
    expect(grrApiServiceMock.get.calls.count()).toBe(1);
  });

  it('queues requests until the data are fetched', () => {
    const deferred = $q.defer();
    spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

    const responses = [];
    grrReflectionService.getRDFValueDescriptor('Duration').then((response) => {
      responses.push(response);
    });

    grrReflectionService.getRDFValueDescriptor('RDFDatetime')
        .then((response) => {
          responses.push(response);
        });

    expect(responses.length).toBe(0);

    deferred.resolve({
      data: {
        items: [
          {
            'doc': 'Duration value stored in seconds internally.',
            'kind': 'primitive',
            'name': 'Duration',
          },
          {
            'doc': 'Date and time.',
            'kind': 'primitive',
            'name': 'RDFDatetime',
          },
        ],
      },
    });
    $rootScope.$apply();

    expect(responses.length).toBe(2);
    expect(responses[0]).toEqual({
      'doc': 'Duration value stored in seconds internally.',
      'kind': 'primitive',
      'name': 'Duration',
    });
    expect(responses[1]).toEqual({
      'doc': 'Date and time.',
      'kind': 'primitive',
      'name': 'RDFDatetime',
    });
  });

  it('returns data with dependencies if opt_withDeps is true', () => {
    const deferred = $q.defer();
    deferred.resolve({
      data: {
        items: [
          {
            'doc': 'Sample struct.',
            'kind': 'struct',
            'name': 'Struct',
            'fields': [
              {'type': 'RDFInteger'},
            ],
          },
          {
            'doc': 'Sample integer.',
            'kind': 'primitive',
            'name': 'RDFInteger',
          },
        ],
      },
    });
    spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

    let descriptors;
    grrReflectionService.getRDFValueDescriptor('Struct', true)
        .then((response) => {
          descriptors = response;
        });
    $rootScope.$apply();

    expect(descriptors['Struct']).toBeDefined();
    expect(descriptors['RDFInteger']).toBeDefined();
  });
});


exports = {};
