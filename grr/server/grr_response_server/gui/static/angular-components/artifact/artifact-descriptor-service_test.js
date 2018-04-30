'use strict';

goog.module('grrUi.artifact.artifactDescriptorServiceTest');

const {ArtifactDescriptorsService} = goog.require('grrUi.artifact.artifactDescriptorsService');
const {artifactModule} = goog.require('grrUi.artifact.artifact');
const {testsModule} = goog.require('grrUi.tests');


describe('grrArtifactDescriptorsService service', () => {
  let $q;
  let $rootScope;
  let grrApiServiceMock;
  let grrArtifactDescriptorsService;


  beforeEach(module(artifactModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');

    grrApiServiceMock = {get: function() {}};
    grrArtifactDescriptorsService =
        $injector.instantiate(ArtifactDescriptorsService, {
          'grrApiService': grrApiServiceMock,
        });
  }));

  const successResponse = {
    data: {
      items: [
        {
          type: 'ArtifactDescriptor',
          value: {
            artifact: {
              value: {
                name: {
                  value: 'foo',
                },
              },
            },
          },
        },
        {
          type: 'ArtifactDescriptor',
          value: {
            artifact: {
              value: {
                name: {
                  value: 'bar',
                },
              },
            },
          },
        },
      ],
    },
  };

  const failureResponse = {
    data: {
      message: 'Oh no!',
    },
  };

  describe('listDescriptors()', () => {
    it('resolves to a dictionary of descriptors on success', (done) => {
      const deferred = $q.defer();
      deferred.resolve(successResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.listDescriptors().then((descriptors) => {
        expect(Object.keys(descriptors)).toEqual(['foo', 'bar']);
        done();
      });
      $rootScope.$apply();
    });

    it('resolves to an error message on error', (done) => {
      const deferred = $q.defer();
      deferred.reject(failureResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.listDescriptors().then(
          () => {}, (message) => {
            expect(message).toBe('Oh no!');
            done();
          });
      $rootScope.$apply();
    });

    it('does not start more than one API requests', () => {
      const deferred1 = $q.defer();
      const deferred2 = $q.defer();
      spyOn(grrApiServiceMock, 'get').and.returnValues(deferred1.promise,
                                                       deferred2.promise);

      grrArtifactDescriptorsService.listDescriptors();
      grrArtifactDescriptorsService.listDescriptors();

      expect(grrApiServiceMock.get.calls.count()).toBe(1);
    });
  });

  describe('getDescriptorByName()', () => {
    it('resolves to a descriptor', (done) => {
      const deferred = $q.defer();
      deferred.resolve(successResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.getDescriptorByName('foo').then(
          (descriptor) => {
            expect(descriptor).toEqual(successResponse.data.items[0]);
            done();
          });
      $rootScope.$apply();
    });

    it('resolves to undefined if descriptor not found', (done) => {
      const deferred = $q.defer();
      deferred.resolve(successResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.getDescriptorByName('something')
          .then((descriptor) => {
            expect(descriptor).toBeUndefined();
            done();
          });
      $rootScope.$apply();
    });

    it('resolve to an error message in case of error', (done) => {
      const deferred = $q.defer();
      deferred.reject(failureResponse);
      spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

      grrArtifactDescriptorsService.getDescriptorByName('something')
          .then(() => {}, (message) => {
            expect(message).toBe('Oh no!');
            done();
          });
      $rootScope.$apply();
    });
  });

  describe('clearCache()', () => {
    it('forces next listDescriptors call to do an API request', () => {
      const deferred1 = $q.defer();
      deferred1.resolve(successResponse);

      const deferred2 = $q.defer();
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


exports = {};
