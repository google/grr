'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.core.reflectionService.ReflectionService');
goog.require('grrUi.tests.module');


describe('AFF4 items provider directive', function() {
  var $rootScope, $q, grrApiServiceMock, grrReflectionService;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');

    grrApiServiceMock = {get: function() {}};
    grrReflectionService = $injector.instantiate(
        grrUi.core.reflectionService.ReflectionService,
        {
          'grrApiService': grrApiServiceMock
        });
  }));

  it('fetches data from the server only once', function() {
    var deferred = $q.defer();
    spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

    grrReflectionService.getRDFValueDescriptor('Duration');
    grrReflectionService.getRDFValueDescriptor('RDFDatetime');
    // Check that only 1 call to API service was made.
    expect(grrApiServiceMock.get.calls.count()).toBe(1);
  });

  it('queues requests until the data are fetched', function() {
    var deferred = $q.defer();
    spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

    var responses = [];
    grrReflectionService.getRDFValueDescriptor('Duration').then(
        function(response) {
          responses.push(response);
        });

    grrReflectionService.getRDFValueDescriptor('RDFDatetime').then(
        function(response) {
          responses.push(response);
        });

    expect(responses.length).toBe(0);

    deferred.resolve({
      'data': {
        'Duration': {
          'doc': 'Duration value stored in seconds internally.',
          'kind': 'primitive',
          'name': 'Duration'
        },
        'RDFDatetime': {
          'doc': 'Date and time.',
          'kind': 'primitive',
          'name': 'RDFDatetime'
        }
      }
    });
    $rootScope.$apply();

    expect(responses.length).toBe(2);
    expect(responses[0]).toEqual({
      'doc': 'Duration value stored in seconds internally.',
      'kind': 'primitive',
      'name': 'Duration'
    });
    expect(responses[1]).toEqual({
      'doc': 'Date and time.',
      'kind': 'primitive',
      'name': 'RDFDatetime'
    });
  });

  it('returns data with dependencies if opt_withDeps is true', function() {
    var deferred = $q.defer();
    deferred.resolve({
      'data': {
        'Struct': {
          'doc': 'Sample struct.',
          'kind': 'struct',
          'name': 'Struct',
          'fields': [
            {'type': 'RDFInteger'}
          ]
        },
        'RDFInteger': {
          'doc': 'Sample integer.',
          'kind': 'primitive',
          'name': 'RDFInteger'
        }
      }
    });
    spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

    var descriptors;
    grrReflectionService.getRDFValueDescriptor('Struct', true).then(
        function(response) {
          descriptors = response;
        });
    $rootScope.$apply();

    expect(descriptors['Struct']).toBeDefined();
    expect(descriptors['RDFInteger']).toBeDefined();
  });

});
