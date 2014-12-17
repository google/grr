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
    grr.state.reason = 'some reason';

    $httpBackend.whenGET('/api/some/path?reason=some+reason').
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
    grr.state.reason = 'some reason';

    $httpBackend.whenGET('/api/some/path?' +
        'key1=value1&key2=value2&reason=some+reason').respond(200);
    grrApiService.get('some/path', {key1: 'value1', key2: 'value2'});
    $httpBackend.flush();
  });
});
