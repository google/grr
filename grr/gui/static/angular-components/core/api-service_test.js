'use strict';

goog.provide('grrUi.core.apiServiceTest');
goog.require('grrUi.core.apiService');
goog.require('grrUi.core.apiService.encodeUrlPath');
goog.require('grrUi.core.apiService.stripTypeInfo');
goog.require('grrUi.core.module');


// TODO(user): Used to test grr.publish calls. Remove as soon as
// this dependency is gone.
var grr = grr || {};


describe('API service', function() {
  var $rootScope, $q, $httpBackend, $interval, grrApiService;

  beforeEach(module(grrUi.core.module.name));

  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    $httpBackend = $injector.get('$httpBackend');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');

    grrApiService.markAuthDone();
  }));

  afterEach(function() {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  describe('encodeUrlPath() function', function() {
    var encodeUrlPath = grrUi.core.apiService.encodeUrlPath;

    it('does not touch slashes and normal characters', function() {
      expect(encodeUrlPath('////')).toBe('////');
      expect(encodeUrlPath('/a/b/c/d/')).toBe('/a/b/c/d/');
    });

    it('encodes "?", "&" and "+" characters', function() {
      expect(encodeUrlPath('/foo?bar=a+b')).toBe('/foo%3Fbar%3Da%2Bb');
    });
  });

  describe('stripTypeInfo() function', function() {
    var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

    it('converts richly typed primitive into a primitive value', function() {
      var richData = {
        'age': 0,
        'mro': [
          'RDFString',
          'object'
        ],
        'type': 'unicode',
        'value': 'label2'
      };

      expect(stripTypeInfo(richData)).toEqual('label2');
    });

    it('converts typed structure into a primitive dictionary', function() {
      var richData = {
        'age': 0,
        'mro': [
          'AFF4ObjectLabel',
          'RDFProtoStruct',
          'RDFStruct',
          'RDFValue',
          'object'
        ],
        'type': 'AFF4ObjectLabel',
        'value': {
          'name': {
            'age': 0,
            'mro': [
              'unicode',
              'basestring',
              'object'
            ],
            'type': 'unicode',
            'value': 'label2'
          }
        }
      };

      expect(stripTypeInfo(richData)).toEqual({'name': 'label2'});
    });

    it('converts richly typed list into list of primitives', function() {
      var richData = [
        {
          'age': 0,
          'mro': [
            'RDFString',
            'object'
          ],
          'type': 'unicode',
        'value': 'label2'
        },
        {
          'age': 0,
          'mro': [
            'RDFString',
            'object'
          ],
          'type': 'unicode',
        'value': 'label3'
        }
      ];


      expect(stripTypeInfo(richData)).toEqual(
        ['label2', 'label3']);
    });

    it('converts list structure field into list of primitives', function() {
      var richData = {
        'age': 0,
        'mro': [
          'AFF4ObjectLabel',
          'RDFProtoStruct',
          'RDFStruct',
          'RDFValue',
          'object'
        ],
        'type': 'AFF4ObjectLabel',
        'value': {
          'name': [
            {
              'age': 0,
              'mro': [
                'unicode',
                'basestring',
                'object'
              ],
              'type': 'unicode',
              'value': 'label2'
            },
            {
              'age': 0,
              'mro': [
                'unicode',
                'basestring',
                'object'
              ],
              'type': 'unicode',
              'value': 'label3'
            }
          ]
        }
      };

      expect(stripTypeInfo(richData)).toEqual({
        'name': ['label2', 'label3']
      });
    });
  });

  describe('head() method', function() {
    it('adds "/api/" to a given url', function() {
      $httpBackend.whenHEAD('/api/some/path').respond(200);
      grrApiService.head('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', function() {
      $httpBackend.whenHEAD('/api/some/path').respond(200);
      grrApiService.head('/some/path');
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.whenHEAD('/api/some/path?key1=value1&key2=value2').
          respond(200);
      grrApiService.head('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.whenHEAD('/api/some/path?' +
          'key1=value1&key2=value2').respond(200);
      grrApiService.head('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('url-escapes the path', function() {
      $httpBackend.whenHEAD(
          '/api/some/path%3Ffoo%26bar?key1=value1&key2=value2').respond(200);
      grrApiService.head('some/path?foo&bar', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });
  });

  describe('get() method', function() {
    it('adds "/api/" to a given url', function() {
      $httpBackend.whenGET('/api/some/path').respond(200);
      grrApiService.get('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', function() {
      $httpBackend.whenGET('/api/some/path').respond(200);
      grrApiService.get('/some/path');
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.whenGET('/api/some/path?key1=value1&key2=value2').
          respond(200);
      grrApiService.get('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.whenGET('/api/some/path?' +
          'key1=value1&key2=value2').respond(200);
      grrApiService.get('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('url-escapes the path', function() {
      $httpBackend.whenGET(
          '/api/some/path%3Ffoo%26bar?key1=value1&key2=value2').respond(200);
      grrApiService.get('some/path?foo&bar', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });
  });

  describe('poll() method', function() {
    it('triggers url once if condition is immediately satisfied', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'state': 'FINISHED'
      });

      grrApiService.poll('some/path', 1000);

      $httpBackend.flush();
      $interval.flush(2000);
      // No requests should be outstanding by this point.
    });

    it('does not call callbacks when cancelled via cancelPoll()', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      var successHandlerCalled = false;
      var failureHandlerCalled = false;
      var finallyHandlerCalled = false;
      var pollPromise = grrApiService.poll('some/path', 1000);

      pollPromise.then(function() {
        successHandlerCalled = true;
      }, function() {
        failureHandlerCalled = true;
      }).finally(function() {
        finallyHandlerCalled = true;
      });
      grrApiService.cancelPoll(pollPromise);

      $httpBackend.flush();
      expect(successHandlerCalled).toBe(false);
      expect(failureHandlerCalled).toBe(false);
      expect(finallyHandlerCalled).toBe(false);
    });

    it('succeeds and returns response if first try succeeds', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED'
      });

      var successHandlerCalled = false;
      grrApiService.poll('some/path', 1000).then(function(response) {
        expect(response['data']).toEqual({
          'foo': 'bar',
          'state': 'FINISHED'
        });
        successHandlerCalled = true;
      });

      $httpBackend.flush();
      expect(successHandlerCalled).toBe(true);
    });

    it('triggers url multiple times if condition is not satisfied', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      grrApiService.poll('some/path', 1000);

      $httpBackend.flush();

      $httpBackend.expectGET('/api/some/path').respond(200, {});
      $interval.flush(2000);
      $httpBackend.flush();
    });

    it('succeeds and returns response if second try succeeds', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      var successHandlerCalled = false;
      grrApiService.poll('some/path', 1000).then(function(response) {
        expect(response['data']).toEqual({
          'foo': 'bar',
          'state': 'FINISHED'
        });
        successHandlerCalled = true;
      });

      $httpBackend.flush();

      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED'
      });
      $interval.flush(2000);
      $httpBackend.flush();

      expect(successHandlerCalled).toBe(true);
    });

    it('fails if first try fails', function() {
      $httpBackend.expectGET('/api/some/path').respond(500);

      var failureHandleCalled = false;
      grrApiService.poll('some/path', 1000).then(function success() {
      }, function failure() {
        failureHandleCalled = true;
      });

      $httpBackend.flush();
      expect(failureHandleCalled).toBe(true);
    });

    it('fails if first try is correct, but second one fails', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      var failureHandleCalled = false;
      grrApiService.poll('some/path', 1000).then(function success() {
      }, function failure() {
        failureHandleCalled = true;
      });

      $httpBackend.flush();

      $httpBackend.expectGET('/api/some/path').respond(500);
      $interval.flush(2000);
      $httpBackend.flush();

      expect(failureHandleCalled).toBe(true);
    });

    it('returns response payload on failure', function() {
      $httpBackend.expectGET('/api/some/path').respond(500, {'foo': 'bar'});

      grrApiService.poll('some/path', 1000).then(function success() {
      }, function failure(response) {
        expect(response['data']).toEqual({'foo': 'bar'});
      });

      $httpBackend.flush();
    });

    it('notifies on every intermediate poll result', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      var notificationCount = 0;
      grrApiService.poll('some/path', 1000).then(
          undefined, undefined,
          function(data) {
            notificationCount += 1;
          });
      expect(notificationCount).toBe(0);

      $httpBackend.flush();
      expect(notificationCount).toBe(1);

      $interval.flush(500);
      expect(notificationCount).toBe(1);

      $httpBackend.expectGET('/api/some/path').respond(200, {});
      $interval.flush(500);
      $httpBackend.flush();
      expect(notificationCount).toBe(2);
    });

    it('does not allow API requests to overlap', function() {
      var notificationCount = 0;
      grrApiService.poll('some/path', 1000).then(
          undefined, undefined,
          function(data) {
            notificationCount += 1;
          });
      expect(notificationCount).toBe(0);

      $interval.flush(2000);
      expect(notificationCount).toBe(0);
    });

    it('does not resolve the promise after cancelPoll() call', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED'
      });

      var successHandlerCalled = false;
      var promise = grrApiService.poll('some/path', 1000).then(
          function(response) {
            successHandlerCalled = true;
          });

      grrApiService.cancelPoll(promise);
      $httpBackend.flush();
      expect(successHandlerCalled).toBe(false);
    });

    it('works correctly on a chained promise', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED'
      });

      var successHandlerCalled = false;
      var finallyHandlerCalled = false;
      grrApiService.poll('some/path', 1000)
          .then(function() { successHandlerCalled = true; }).
          catch(function() {}).
          finally(function() { finallyHandlerCalled = true; });

      $httpBackend.flush();
      expect(finallyHandlerCalled).toBe(true);
      expect(successHandlerCalled).toBe(true);
    });

    it('allows cancelPoll to be called on a chained promise', function() {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED'
      });

      var successHandlerCalled = false;
      var finallyHandlerCalled = false;
      var promise = grrApiService.poll('some/path', 1000)
          .then(function() { successHandlerCalled = true; }).
          catch(function() {}).
          finally(function() { finallyHandlerCalled = true; });

      grrApiService.cancelPoll(promise);
      $httpBackend.flush();
      expect(finallyHandlerCalled).toBe(false);
      expect(successHandlerCalled).toBe(false);
    });
  });

  describe('cancelPoll() method', function() {
    it('raises if the promise does not have "cancel" attribute', function() {
      var deferred = $q.defer();
      expect(function() {
        grrApiService.cancelPoll(deferred.promise);
      }).toThrow(new Error('Invalid promise to cancel: not cancelable.'));
    });
  });

  describe('delete() method', function() {
    it('adds "/api/" to a given url', function() {
      $httpBackend.expectDELETE('/api/some/path').respond(200);
      grrApiService.delete('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', function() {
      $httpBackend.expectDELETE('/api/some/path').respond(200);
      grrApiService.delete('/some/path');
      $httpBackend.flush();
    });

    it('passes user-provided data in the request', function() {
      $httpBackend.expect(
          'DELETE', '/api/some/path', {key1: 'value1', key2: 'value2'})
              .respond(200);
      grrApiService.delete('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });


    it('url-escapes the path', function() {
      $httpBackend.expectDELETE(
          '/api/some/path%3Ffoo%26bar').respond(200);
      grrApiService.delete('some/path?foo&bar');
      $httpBackend.flush();
    });

    it('doesn\'t send request body if no payload provided', function() {
      $httpBackend.expect('DELETE', '/api/some/path', function(data) {
        return angular.isUndefined(data);
      }).respond(200);
      grrApiService.delete('some/path');
      $httpBackend.flush();
    });
  });

  describe('patch() method', function() {
    it('adds "/api/" to a given url', function() {
      $httpBackend.expectPATCH('/api/some/path').respond(200);
      grrApiService.patch('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', function() {
      $httpBackend.expectPATCH('/api/some/path').respond(200);
      grrApiService.patch('/some/path');
      $httpBackend.flush();
    });

    it('passes user-provided data in the request', function() {
      $httpBackend.expect(
          'PATCH', '/api/some/path', {key1: 'value1', key2: 'value2'})
              .respond(200);
      grrApiService.patch('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });


    it('url-escapes the path', function() {
      $httpBackend.expectPATCH(
          '/api/some/path%3Ffoo%26bar').respond(200);
      grrApiService.patch('some/path?foo&bar');
      $httpBackend.flush();
    });
  });

  describe('post() method', function() {
    it('adds "/api/" to a given url', function() {
      $httpBackend.whenPOST('/api/some/path').respond(200);
      grrApiService.post('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', function() {
      $httpBackend.whenPOST('/api/some/path').respond(200);
      grrApiService.post('/some/path', {});
      $httpBackend.flush();
    });

    it('strips type info from params if opt_stripTypeInfo is true', function() {
      var richData = {
        'age': 0,
        'mro': [
          'AFF4ObjectLabel',
          'RDFProtoStruct',
          'RDFStruct',
          'RDFValue',
          'object'
        ],
        'type': 'AFF4ObjectLabel',
        'value': {
          'name': {
            'age': 0,
            'mro': [
              'unicode',
              'basestring',
              'object'
            ],
            'type': 'unicode',
            'value': 'label2'
          }
        }
      };

      $httpBackend.whenPOST('/api/some/path', {name: 'label2'}).respond(200);
      grrApiService.post('some/path', richData, true);
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.expectPOST(
          '/api/some/path', {key1: 'value1', key2: 'value2'}).respond(200);

      grrApiService.post('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('url-escapes the path', function() {
      $httpBackend.whenPOST(
          '/api/some/path%3Ffoo%26bar').respond(200);
      grrApiService.post('some/path?foo&bar', {});
      $httpBackend.flush();
    });

    it('url-escapes the path when files are uploaded', function() {
      $httpBackend.whenPOST('/api/some/path%3Ffoo%26bar').respond(200);
      grrApiService.post('some/path?foo&bar', {}, false, {'file1': 'blah'});
      $httpBackend.flush();
    });
  });

  describe('downloadFile() method', function() {
    afterEach(function() {
      // We have to clean document's body to remove an iframe generated
      // by the downloadFile call.
      $(document.body).html('');
    });

    it('sends HEAD request first to check if URL is accessible', function() {
      $httpBackend.expectHEAD('/api/some/path').respond(200);

      grrApiService.downloadFile('some/path');

      $httpBackend.flush();
    });

    it('sends query parameters in the HEAD request', function() {
      $httpBackend.expectHEAD('/api/some/path?abra=cadabra&foo=bar').respond(
          200);

      grrApiService.downloadFile('some/path', {'foo': 'bar',
                                               'abra': 'cadabra'});

      $httpBackend.flush();
    });

    it('url-escapes the path', function() {
      $httpBackend.expectHEAD(
          '/api/some/path%3Ffoo%26bar?key1=value1&key2=value2').respond(200);
      grrApiService.downloadFile('some/path?foo&bar',
                                 {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('rejects promise if HEAD request fails', function() {
      $httpBackend.whenHEAD('/api/some/path').respond(500);

      var promiseRejected = false;
      var promise = grrApiService.downloadFile('some/path');
      promise.then(function success() {},
                   function failure() { promiseRejected = true; });

      $httpBackend.flush();

      expect(promiseRejected).toBe(true);
    });

    it('broadcasts subject/reason from UnauthorizedAccess HEAD response',
       function() {
      $httpBackend.whenHEAD('/api/some/path').respond(403, {}, {
        'x-grr-unauthorized-access-subject': 'some subject',
        'x-grr-unauthorized-access-reason': 'some reason'});

      spyOn($rootScope, '$broadcast');
      grrApiService.downloadFile('some/path');
      $httpBackend.flush();

      expect($rootScope.$broadcast).toHaveBeenCalledWith(
          grrUi.core.apiService.UNAUTHORIZED_API_RESPONSE_EVENT,
          {
            subject: 'some subject', reason: 'some reason'
          });
    });

    it('creates an iframe request if HEAD succeeds', function() {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      grrApiService.downloadFile('some/path');
      $httpBackend.flush();

      expect($('iframe').attr('src')).toBe('/api/some/path');
    });

    it('propagates query option to iframe "src" attribute', function() {
      $httpBackend.whenHEAD('/api/some/path?abra=cadabra&foo=bar').respond(200);

      grrApiService.downloadFile('some/path',
                                 {'foo': 'bar', 'abra': 'cadabra'});
      $httpBackend.flush();

      expect($('iframe').attr('src')).toBe('/api/some/path?abra=cadabra&foo=bar');
    });

    it('fails if same-origin-policy error is thrown when accessing iframe',
        function() {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      var promiseRejected = false;
      var promise = grrApiService.downloadFile('some/path');
      promise.then(function success() {},
                   function failure() { promiseRejected = true; });
      $httpBackend.flush();

      // If iframe request fails, iframe will sho a standard error page
      // which will have a different origin and raise on access.
      Object.defineProperty($('iframe')[0].contentWindow.document,
                            'readyState',
                            {
                              __proto__: null,
                              get: function() {
                                throw new Error('Same origin policy error');
                              }
                            });
      $interval.flush(1000);

      expect(promiseRejected).toBe(true);
    });

    it('cancels the interval timer if iframe request fails', function() {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      spyOn($interval, 'cancel').and.returnValue();
      grrApiService.downloadFile('some/path');
      $httpBackend.flush();

      Object.defineProperty($('iframe')[0].contentWindow.document,
                            'readyState',
                            {
                              __proto__: null,
                              get: function() {
                                throw new Error('Same origin policy error');
                              }
                            });
      $interval.flush(1000);

      expect($interval.cancel).toHaveBeenCalled();
    });

    it('succeeds if iframe request succeeds', function() {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      var promiseSucceeded = false;
      var promise = grrApiService.downloadFile('some/path');
      promise.then(function success() { promiseSucceeded = true; });
      $httpBackend.flush();

      Object.defineProperty($('iframe')[0].contentWindow.document,
                            'readyState',
                            {
                              __proto__: null,
                              get: function() {
                                return 'complete';
                              }
                            });
      $interval.flush(1000);

      expect(promiseSucceeded).toBe(true);
    });

    it('cancels the interval timer if iframe request succeeds', function() {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      spyOn($interval, 'cancel').and.returnValue();
      grrApiService.downloadFile('some/path');
      $httpBackend.flush();

      Object.defineProperty($('iframe')[0].contentWindow.document,
                            'readyState',
                            {
                              __proto__: null,
                              get: function() {
                                return 'complete';
                              }
                            });
      $interval.flush(1000);

      expect($interval.cancel).toHaveBeenCalled();
    });
  });
});
