'use strict';

goog.require('grrUi.core.apiService.encodeUrlPath');
goog.require('grrUi.core.apiService.stripTypeInfo');
goog.require('grrUi.core.module');

var grr = grr || {};

describe('API service', function() {
  var $httpBackend, $interval, grrApiService;

  beforeEach(module(grrUi.core.module.name));

  beforeEach(inject(function($injector) {
    $httpBackend = $injector.get('$httpBackend');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');

    grr.state = {};
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

    it('uses grr.state.reason in requests', function() {
      grr.state.reason = 'some reason ';

      $httpBackend.whenHEAD('/api/some/path?reason=some+reason+').
          respond(200);
      grrApiService.head('some/path');
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.whenHEAD('/api/some/path?key1=value1&key2=value2').
          respond(200);
      grrApiService.head('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('passes user-provided headers and reason in the request', function() {
      grr.state.reason = 'some reason ';

      $httpBackend.whenHEAD('/api/some/path?' +
          'key1=value1&key2=value2&reason=some+reason+').respond(200);
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

    it('uses grr.state.reason in requests', function() {
      grr.state.reason = 'some reason ';

      $httpBackend.whenGET('/api/some/path?reason=some+reason+').
          respond(200);
      grrApiService.get('some/path');
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.whenGET('/api/some/path?key1=value1&key2=value2').
          respond(200);
      grrApiService.get('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('passes user-provided headers and reason in the request', function() {
      grr.state.reason = 'some reason ';

      $httpBackend.whenGET('/api/some/path?' +
          'key1=value1&key2=value2&reason=some+reason+').respond(200);
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

  describe('delete() method', function() {
    it('adds "/api/" to a given url', function() {
      $httpBackend.whenDELETE('/api/some/path').respond(200);
      grrApiService.delete('some/path');
      $httpBackend.flush();
    });

    it('adds "/api/" to a given url starting with "/"', function() {
      $httpBackend.whenDELETE('/api/some/path').respond(200);
      grrApiService.delete('/some/path');
      $httpBackend.flush();
    });

    it('uses grr.state.reason in requests', function() {
      grr.state.reason = 'some reason ';

      $httpBackend.whenDELETE('/api/some/path?reason=some+reason+').
          respond(200);
      grrApiService.delete('some/path');
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.whenDELETE('/api/some/path?key1=value1&key2=value2').
          respond(200);
      grrApiService.delete('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('passes user-provided headers and reason in the request', function() {
      grr.state.reason = 'some reason ';

      $httpBackend.whenDELETE('/api/some/path?' +
          'key1=value1&key2=value2&reason=some+reason+').respond(200);
      grrApiService.delete('some/path', {key1: 'value1', key2: 'value2'});
      $httpBackend.flush();
    });

    it('url-escapes the path', function() {
      $httpBackend.whenDELETE(
          '/api/some/path%3Ffoo%26bar?key1=value1&key2=value2').respond(200);
      grrApiService.delete('some/path?foo&bar',
                           {key1: 'value1', key2: 'value2'});
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

    it('uses url-encoded grr.state.reason in requests', function() {
      grr.state.reason = '区最 unicode reason ';

      $httpBackend.expectPOST('/api/some/path', {}, function(headers) {
        return headers[
            'X-GRR-REASON'] == '%E5%8C%BA%E6%9C%80%20unicode%20reason%20';
      }).respond(200);
      grrApiService.post('some/path');
      $httpBackend.flush();
    });

    it('passes user-provided headers in the request', function() {
      $httpBackend.whenPOST(
          '/api/some/path', {key1: 'value1', key2: 'value2'}).
              respond(200);
      grrApiService.post('some/path', {key1: 'value1', key2: 'value2'});
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

    it('passes user-provided headers and url-encoded reason in the request',
        function() {
      grr.state.reason = '区最 unicode reason ';
      $httpBackend.expectPOST(
          '/api/some/path',
          {key1: 'value1', key2: 'value2'}, function(headers) {
            return headers[
                'X-GRR-REASON'] == '%E5%8C%BA%E6%9C%80%20unicode%20reason%20';
          }).respond(200);

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

    it('uses subject/reason from UnauthorizedAccess HEAD response', function() {
      $httpBackend.whenHEAD('/api/some/path').respond(403, {}, {
        'x-grr-unauthorized-access-subject': 'some subject',
        'x-grr-unauthorized-access-reason': 'some reason'});

      grr.publish = jasmine.createSpy('publish').and.returnValue();

      var promise = grrApiService.downloadFile('some/path');
      $httpBackend.flush();

      expect(grr.publish).toHaveBeenCalledWith('unauthorized',
                                               'some subject',
                                               'some reason');
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
