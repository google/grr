'use strict';

goog.require('grrUi.artifact.artifactDescriptorsService.ArtifactDescriptorsService');
goog.require('grrUi.artifact.module');
goog.require('grrUi.tests.module');


describe('grrArtifactDescriptorsService service', function() {
  var $rootScope, $q, grrApiServiceMock, grrArtifactDescriptorsService;

  beforeEach(module(grrUi.artifact.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');

    grrApiServiceMock = {get: function() {}};
    grrArtifactDescriptorsService = $injector.instantiate(
        grrUi.artifact.artifactDescriptorsService.ArtifactDescriptorsService,
        {
          'grrApiService': grrApiServiceMock
        });
  }));

  var successResponse = {
    data: {
      items: [
        {
          type: 'ArtifactDescriptor',
          value: {
            artifact: {
              value: {
                name: {
                  value: 'foo'
                }
              }
            }
          }
        },
        {
          type: 'ArtifactDescriptor',
          value: {
            artifact: {
              value: {
                name: {
                  value: 'bar'
                }
              }
            }
          }
        }
      ]
    }
  };

  var failureResponse = {
    data: {
      message: 'Oh no!'
    }
  };

  describe('listDescriptors()', function() {
    it('resolves to a dictionary of descriptors on success', function(done) {
      var deferred = $q.defer();
      deferred.resolve(successResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.listDescriptors().then(function(descriptors) {
        expect(Object.keys(descriptors)).toEqual(['foo', 'bar']);
        done();
      });
      $rootScope.$apply();
    });

    it('resolves to an error message on error', function(done) {
      var deferred = $q.defer();
      deferred.reject(failureResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.listDescriptors().then(
          function success() {},
          function faiure(message) {
            expect(message).toBe('Oh no!');
            done();
          });
      $rootScope.$apply();
    });

    it('does not start more than one API requests', function() {
      var deferred1 = $q.defer();
      var deferred2 = $q.defer();
      spyOn(grrApiServiceMock, 'get').and.returnValues(deferred1.promise,
                                                       deferred2.promise);

      grrArtifactDescriptorsService.listDescriptors();
      grrArtifactDescriptorsService.listDescriptors();

      expect(grrApiServiceMock.get.calls.count()).toBe(1);
    });
  });

  describe('getDescriptorByName()', function() {
    it('resolves to a descriptor', function(done) {
      var deferred = $q.defer();
      deferred.resolve(successResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.getDescriptorByName('foo').then(
          function(descriptor) {
            expect(descriptor).toEqual(successResponse.data.items[0]);
            done();
          });
      $rootScope.$apply();
    });

    it('resolves to undefined if descriptor not found', function(done) {
      var deferred = $q.defer();
      deferred.resolve(successResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.getDescriptorByName('something').then(
          function(descriptor) {
            expect(descriptor).toBeUndefined();
            done();
          });
      $rootScope.$apply();
    });

    it('resolve to an error message in case of error', function(done) {
      var deferred = $q.defer();
      deferred.reject(failureResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.getDescriptorByName('something').then(
          function success() {},
          function failure(message) {
            expect(message).toBe('Oh no!');
            done();
          });
      $rootScope.$apply();
    });
  });

  describe('clearCache()', function() {
    it('forces next listDescriptors call to do an API request', function() {
      var deferred1 = $q.defer();
      deferred1.resolve(successResponse);

      var deferred2 = $q.defer();
      deferred2.resolve(successResponse);

      spyOn(grrApiServiceMock, 'get').and.returnValues(deferred1.promise,
                                                       deferred2.promise);

      grrArtifactDescriptorsService.listDescriptors();
      $rootScope.$apply();

      grrArtifactDescriptorsService.clearCache();
      grrArtifactDescriptorsService.listDescriptors();
      $rootScope.$apply();

      expect(grrApiServiceMock.get.calls.count()).toBe(2);
    });
  });
});
