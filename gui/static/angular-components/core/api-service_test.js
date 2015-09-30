'use strict';

goog.require('grrUi.core.module');

var grr = grr || {};

describe('API service', function() {
  var $httpBackend, grrApiService;

  beforeEach(module(grrUi.core.module.name));

  beforeEach(inject(function($injector) {
    $httpBackend = $injector.get('$httpBackend');
    grrApiService = $injector.get('grrApiService');

    grr.state = {};
  }));

  afterEach(function() {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  describe('stripTypeInfo() method', function() {
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

      expect(grrApiService.stripTypeInfo(richData)).toEqual('label2');
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

      expect(grrApiService.stripTypeInfo(richData)).toEqual({'name': 'label2'});
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


      expect(grrApiService.stripTypeInfo(richData)).toEqual(
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

      expect(grrApiService.stripTypeInfo(richData)).toEqual({
        'name': ['label2', 'label3']
      });
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

  });
});
