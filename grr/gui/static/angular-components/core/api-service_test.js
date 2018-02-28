'use strict';

goog.module('grrUi.core.apiServiceTest');

const {coreModule} = goog.require('grrUi.core.core');
const {encodeUrlPath, stripTypeInfo, UNAUTHORIZED_API_RESPONSE_EVENT} = goog.require('grrUi.core.apiService');


describe('API service', () => {
  let $httpBackend;
  let $interval;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module(coreModule.name));

  beforeEach(inject(($injector) => {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    $httpBackend = $injector.get('$httpBackend');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');

    grrApiService.markAuthDone();
  }));

  afterEach(() => {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  describe('encodeUrlPath() function', () => {

    it('does not touch slashes and normal characters', () => {
      expect(encodeUrlPath('////')).toBe('////');
      expect(encodeUrlPath('/a/b/c/d/')).toBe('/a/b/c/d/');
    });

    it('encodes "?", "&" and "+" characters', () => {
      expect(encodeUrlPath('/foo?bar=a+b')).toBe('/foo%3Fbar%3Da%2Bb');
    });
  });

  describe('stripTypeInfo() function', () => {

    it('converts richly typed primitive into a primitive value', () => {
      const richData = {
        'age': 0,
        'mro': [
          'RDFString',
          'object',
        ],
        'type': 'unicode',
        'value': 'label2',
      };

      expect(stripTypeInfo(richData)).toEqual('label2');
    });

    it('converts typed structure into a primitive dictionary', () => {
      const richData = {
        'age': 0,
        'mro': [
          'AFF4ObjectLabel',
          'RDFProtoStruct',
          'RDFStruct',
          'RDFValue',
          'object',
        ],
        'type': 'AFF4ObjectLabel',
        'value': {
          'name': {
            'age': 0,
            'mro': [
              'unicode',
              'basestring',
              'object',
            ],
            'type': 'unicode',
            'value': 'label2',
          },
        },
      };

      expect(stripTypeInfo(richData)).toEqual({'name': 'label2'});
    });

    it('converts richly typed list into list of primitives', () => {
      const richData = [
        {
          'age': 0,
          'mro': [
            'RDFString',
            'object',
          ],
          'type': 'unicode',
          'value': 'label2',
        },
        {
          'age': 0,
          'mro': [
            'RDFString',
            'object',
          ],
          'type': 'unicode',
          'value': 'label3',
        },
      ];


      expect(stripTypeInfo(richData)).toEqual(
        ['label2', 'label3']);
    });

    it('converts list structure field into list of primitives', () => {
      const richData = {
        'age': 0,
        'mro': [
          'AFF4ObjectLabel',
          'RDFProtoStruct',
          'RDFStruct',
          'RDFValue',
          'object',
        ],
        'type': 'AFF4ObjectLabel',
        'value': {
          'name': [
            {
              'age': 0,
              'mro': [
                'unicode',
                'basestring',
                'object',
              ],
              'type': 'unicode',
              'value': 'label2',
            },
            {
              'age': 0,
              'mro': [
                'unicode',
                'basestring',
                'object',
              ],
              'type': 'unicode',
              'value': 'label3',
            },
          ],
        },
      };

      expect(stripTypeInfo(richData)).toEqual({
        'name': ['label2', 'label3'],
      });
    });
  });

  describe('head() method', () => {
    it('adds "/api/" to a given url', () => {
      $httpBackend.whenHEAD('/api/some/path').respond(200);
      grrApiService.head('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', () => {
      $httpBackend.whenHEAD('/api/some/path').respond(200);
      grrApiService.head('/some/path');
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', () => {
      $httpBackend.whenHEAD('/api/some/path?key1=value1&key2=value2').
          respond(200);
      grrApiService.head('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', () => {
      $httpBackend.whenHEAD('/api/some/path?' +
          'key1=value1&key2=value2').respond(200);
      grrApiService.head('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('url-escapes the path', () => {
      $httpBackend.whenHEAD(
          '/api/some/path%3Ffoo%26bar?key1=value1&key2=value2').respond(200);
      grrApiService.head('some/path?foo&bar', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });
  });

  describe('get() method', () => {
    it('adds "/api/" to a given url', () => {
      $httpBackend.whenGET('/api/some/path').respond(200);
      grrApiService.get('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', () => {
      $httpBackend.whenGET('/api/some/path').respond(200);
      grrApiService.get('/some/path');
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', () => {
      $httpBackend.whenGET('/api/some/path?key1=value1&key2=value2').
          respond(200);
      grrApiService.get('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', () => {
      $httpBackend.whenGET('/api/some/path?' +
          'key1=value1&key2=value2').respond(200);
      grrApiService.get('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('url-escapes the path', () => {
      $httpBackend.whenGET(
          '/api/some/path%3Ffoo%26bar?key1=value1&key2=value2').respond(200);
      grrApiService.get('some/path?foo&bar', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });
  });

  describe('poll() method', () => {
    it('triggers url once if condition is immediately satisfied', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'state': 'FINISHED',
      });

      grrApiService.poll('some/path', 1000);

      $httpBackend.flush();
      $interval.flush(2000);
      // No requests should be outstanding by this point.
    });

    it('does not call callbacks when cancelled via cancelPoll()', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      let successHandlerCalled = false;
      let failureHandlerCalled = false;
      let finallyHandlerCalled = false;
      const pollPromise = grrApiService.poll('some/path', 1000);

      pollPromise
          .then(
              () => {
                successHandlerCalled = true;
              },
              () => {
                failureHandlerCalled = true;
              })
          .finally(() => {
            finallyHandlerCalled = true;
          });
      grrApiService.cancelPoll(pollPromise);

      $httpBackend.flush();
      expect(successHandlerCalled).toBe(false);
      expect(failureHandlerCalled).toBe(false);
      expect(finallyHandlerCalled).toBe(false);
    });

    it('succeeds and returns response if first try succeeds', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED',
      });

      let successHandlerCalled = false;
      grrApiService.poll('some/path', 1000).then((response) => {
        expect(response['data']).toEqual({
          'foo': 'bar',
          'state': 'FINISHED',
        });
        successHandlerCalled = true;
      });

      $httpBackend.flush();
      expect(successHandlerCalled).toBe(true);
    });

    it('triggers url multiple times if condition is not satisfied', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      grrApiService.poll('some/path', 1000);

      $httpBackend.flush();

      $httpBackend.expectGET('/api/some/path').respond(200, {});
      $interval.flush(2000);
      $httpBackend.flush();
    });

    it('succeeds and returns response if second try succeeds', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      let successHandlerCalled = false;
      grrApiService.poll('some/path', 1000).then((response) => {
        expect(response['data']).toEqual({
          'foo': 'bar',
          'state': 'FINISHED',
        });
        successHandlerCalled = true;
      });

      $httpBackend.flush();

      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED',
      });
      $interval.flush(2000);
      $httpBackend.flush();

      expect(successHandlerCalled).toBe(true);
    });

    it('fails if first try fails', () => {
      $httpBackend.expectGET('/api/some/path').respond(500);

      let failureHandleCalled = false;
      grrApiService.poll('some/path', 1000).then(() => {}, () => {
        failureHandleCalled = true;
      });

      $httpBackend.flush();
      expect(failureHandleCalled).toBe(true);
    });

    it('fails if first try is correct, but second one fails', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      let failureHandleCalled = false;
      grrApiService.poll('some/path', 1000).then(() => {}, () => {
        failureHandleCalled = true;
      });

      $httpBackend.flush();

      $httpBackend.expectGET('/api/some/path').respond(500);
      $interval.flush(2000);
      $httpBackend.flush();

      expect(failureHandleCalled).toBe(true);
    });

    it('returns response payload on failure', () => {
      $httpBackend.expectGET('/api/some/path').respond(500, {'foo': 'bar'});

      grrApiService.poll('some/path', 1000).then(() => {}, (response) => {
        expect(response['data']).toEqual({'foo': 'bar'});
      });

      $httpBackend.flush();
    });

    it('notifies on every intermediate poll result', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {});

      let notificationCount = 0;
      grrApiService.poll('some/path', 1000)
          .then(undefined, undefined, (data) => {
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

    it('does not allow API requests to overlap', () => {
      const deferred = $q.defer();
      spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

      grrApiService.poll('some/path', 1000);
      expect(grrApiService.get).toHaveBeenCalledTimes(1);

      $interval.flush(2000);
      expect(grrApiService.get).toHaveBeenCalledTimes(1);
    });

    it('does not resolve the promise after cancelPoll() call', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED',
      });

      let successHandlerCalled = false;
      const promise = grrApiService.poll('some/path', 1000).then((response) => {
        successHandlerCalled = true;
      });

      grrApiService.cancelPoll(promise);
      $httpBackend.flush();
      expect(successHandlerCalled).toBe(false);
    });

    it('works correctly on a chained promise', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED',
      });

      let successHandlerCalled = false;
      let finallyHandlerCalled = false;
      grrApiService.poll('some/path', 1000)
          .then(() => {
            successHandlerCalled = true;
          })
          .catch(() => {})
          .finally(() => {
            finallyHandlerCalled = true;
          });

      $httpBackend.flush();
      expect(finallyHandlerCalled).toBe(true);
      expect(successHandlerCalled).toBe(true);
    });

    it('allows cancelPoll to be called on a chained promise', () => {
      $httpBackend.expectGET('/api/some/path').respond(200, {
        'foo': 'bar',
        'state': 'FINISHED',
      });

      let successHandlerCalled = false;
      let finallyHandlerCalled = false;
      const promise = grrApiService.poll('some/path', 1000)
                          .then(() => {
                            successHandlerCalled = true;
                          })
                          .catch(() => {})
                          .finally(() => {
                            finallyHandlerCalled = true;
                          });

      grrApiService.cancelPoll(promise);
      $httpBackend.flush();
      expect(finallyHandlerCalled).toBe(false);
      expect(successHandlerCalled).toBe(false);
    });
  });

  describe('cancelPoll() method', () => {
    it('raises if the promise does not have "cancel" attribute', () => {
      const deferred = $q.defer();
      expect(() => {
        grrApiService.cancelPoll(deferred.promise);
      }).toThrow(new Error('Invalid promise to cancel: not cancelable.'));
    });
  });

  describe('delete() method', () => {
    it('adds "/api/" to a given url', () => {
      $httpBackend.expectDELETE('/api/some/path').respond(200);
      grrApiService.delete('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', () => {
      $httpBackend.expectDELETE('/api/some/path').respond(200);
      grrApiService.delete('/some/path');
      $httpBackend.flush();
    });

    it('passes user-provided data in the request', () => {
      $httpBackend.expect(
          'DELETE', '/api/some/path', {key1: 'value1', key2: 'value2'})
              .respond(200);
      grrApiService.delete('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });


    it('url-escapes the path', () => {
      $httpBackend.expectDELETE(
          '/api/some/path%3Ffoo%26bar').respond(200);
      grrApiService.delete('some/path?foo&bar');
      $httpBackend.flush();
    });

    it('doesn\'t send request body if no payload provided', () => {
      $httpBackend
          .expect(
              'DELETE', '/api/some/path', (data) => angular.isUndefined(data))
          .respond(200);
      grrApiService.delete('some/path');
      $httpBackend.flush();
    });
  });

  describe('patch() method', () => {
    it('adds "/api/" to a given url', () => {
      $httpBackend.expectPATCH('/api/some/path').respond(200);
      grrApiService.patch('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', () => {
      $httpBackend.expectPATCH('/api/some/path').respond(200);
      grrApiService.patch('/some/path');
      $httpBackend.flush();
    });

    it('passes user-provided data in the request', () => {
      $httpBackend.expect(
          'PATCH', '/api/some/path', {key1: 'value1', key2: 'value2'})
              .respond(200);
      grrApiService.patch('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });


    it('url-escapes the path', () => {
      $httpBackend.expectPATCH(
          '/api/some/path%3Ffoo%26bar').respond(200);
      grrApiService.patch('some/path?foo&bar');
      $httpBackend.flush();
    });
  });

  describe('post() method', () => {
    it('adds "/api/" to a given url', () => {
      $httpBackend.whenPOST('/api/some/path').respond(200);
      grrApiService.post('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', () => {
      $httpBackend.whenPOST('/api/some/path').respond(200);
      grrApiService.post('/some/path', {});
      $httpBackend.flush();
    });

    it('strips type info from params if opt_stripTypeInfo is true', () => {
      const richData = {
        'age': 0,
        'mro': [
          'AFF4ObjectLabel',
          'RDFProtoStruct',
          'RDFStruct',
          'RDFValue',
          'object',
        ],
        'type': 'AFF4ObjectLabel',
        'value': {
          'name': {
            'age': 0,
            'mro': [
              'unicode',
              'basestring',
              'object',
            ],
            'type': 'unicode',
            'value': 'label2',
          },
        },
      };

      $httpBackend.whenPOST('/api/some/path', {name: 'label2'}).respond(200);
      grrApiService.post('some/path', richData, true);
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', () => {
      $httpBackend.expectPOST(
          '/api/some/path', {key1: 'value1', key2: 'value2'}).respond(200);

      grrApiService.post('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('url-escapes the path', () => {
      $httpBackend.whenPOST(
          '/api/some/path%3Ffoo%26bar').respond(200);
      grrApiService.post('some/path?foo&bar', {});
      $httpBackend.flush();
    });

    it('url-escapes the path when files are uploaded', () => {
      $httpBackend.whenPOST('/api/some/path%3Ffoo%26bar').respond(200);
      grrApiService.post('some/path?foo&bar', {}, false, {'file1': 'blah'});
      $httpBackend.flush();
    });
  });

  describe('downloadFile() method', () => {
    afterEach(() => {
      // We have to clean document's body to remove an iframe generated
      // by the downloadFile call.
      $(document.body).html('');
    });

    it('sends HEAD request first to check if URL is accessible', () => {
      $httpBackend.expectHEAD('/api/some/path').respond(200);

      grrApiService.downloadFile('some/path');

      $httpBackend.flush();
    });

    it('sends query parameters in the HEAD request', () => {
      $httpBackend.expectHEAD('/api/some/path?abra=cadabra&foo=bar').respond(
          200);

      grrApiService.downloadFile('some/path', {'foo': 'bar',
                                               'abra': 'cadabra'});

      $httpBackend.flush();
    });

    it('url-escapes the path', () => {
      $httpBackend.expectHEAD(
          '/api/some/path%3Ffoo%26bar?key1=value1&key2=value2').respond(200);
      grrApiService.downloadFile('some/path?foo&bar',
                                 {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('rejects promise if HEAD request fails', () => {
      $httpBackend.whenHEAD('/api/some/path').respond(500);

      let promiseRejected = false;
      const promise = grrApiService.downloadFile('some/path');
      promise.then(() => {}, () => {
        promiseRejected = true;
      });

      $httpBackend.flush();

      expect(promiseRejected).toBe(true);
    });

    it('broadcasts subject/reason from UnauthorizedAccess HEAD response',
       () => {
         $httpBackend.whenHEAD('/api/some/path').respond(403, {}, {
           'x-grr-unauthorized-access-subject': 'some subject',
           'x-grr-unauthorized-access-reason': 'some reason'
         });

         spyOn($rootScope, '$broadcast');
         grrApiService.downloadFile('some/path');
         $httpBackend.flush();

         expect($rootScope.$broadcast)
             .toHaveBeenCalledWith(UNAUTHORIZED_API_RESPONSE_EVENT, {
               subject: 'some subject',
               reason: 'some reason',
             });
       });

    it('creates an iframe request if HEAD succeeds', () => {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      grrApiService.downloadFile('some/path');
      $httpBackend.flush();

      expect($('iframe').attr('src')).toBe('/api/some/path');
    });

    it('propagates query option to iframe "src" attribute', () => {
      $httpBackend.whenHEAD('/api/some/path?abra=cadabra&foo=bar').respond(200);

      grrApiService.downloadFile('some/path',
                                 {'foo': 'bar', 'abra': 'cadabra'});
      $httpBackend.flush();

      expect($('iframe').attr('src')).toBe('/api/some/path?abra=cadabra&foo=bar');
    });

    it('fails if same-origin-policy error is thrown when accessing iframe',
       () => {
         $httpBackend.whenHEAD('/api/some/path').respond(200);

         let promiseRejected = false;
         const promise = grrApiService.downloadFile('some/path');
         promise.then(() => {}, () => {
           promiseRejected = true;
         });
         $httpBackend.flush();

         // If iframe request fails, iframe will sho a standard error page
         // which will have a different origin and raise on access.
         Object.defineProperty(
             $('iframe')[0].contentWindow.document, 'readyState', {
               __proto__: null,
               get: function() {
                 throw new Error('Same origin policy error');
               },
             });
         $interval.flush(1000);

         expect(promiseRejected).toBe(true);
       });

    it('cancels the interval timer if iframe request fails', () => {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      spyOn($interval, 'cancel').and.returnValue();
      grrApiService.downloadFile('some/path');
      $httpBackend.flush();

      Object.defineProperty(
          $('iframe')[0].contentWindow.document, 'readyState', {
            __proto__: null,
            get: function() {
              throw new Error('Same origin policy error');
            },
          });
      $interval.flush(1000);

      expect($interval.cancel).toHaveBeenCalled();
    });

    it('succeeds if iframe request succeeds', () => {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      let promiseSucceeded = false;
      const promise = grrApiService.downloadFile('some/path');
      promise.then(() => {
        promiseSucceeded = true;
      });
      $httpBackend.flush();

      Object.defineProperty(
          $('iframe')[0].contentWindow.document, 'readyState', {
            __proto__: null,
            get: function() {
              return 'complete';
            },
          });
      $interval.flush(1000);

      expect(promiseSucceeded).toBe(true);
    });

    it('cancels the interval timer if iframe request succeeds', () => {
      $httpBackend.whenHEAD('/api/some/path').respond(200);

      spyOn($interval, 'cancel').and.returnValue();
      grrApiService.downloadFile('some/path');
      $httpBackend.flush();

      Object.defineProperty(
          $('iframe')[0].contentWindow.document, 'readyState', {
            __proto__: null,
            get: function() {
              return 'complete';
            },
          });
      $interval.flush(1000);

      expect($interval.cancel).toHaveBeenCalled();
    });
  });
});


exports = {};
