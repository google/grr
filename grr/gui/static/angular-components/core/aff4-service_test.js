'use strict';

goog.require('grrUi.core.module');

var grr = grr || {};

describe('AFF4 service', function() {
  var $httpBackend, grrAff4Service;

  beforeEach(module(grrUi.core.module.name));

  beforeEach(inject(function($injector) {
    $httpBackend = $injector.get('$httpBackend');
    grrAff4Service = $injector.get('grrAff4Service');

    grr.state = {};
  }));

  afterEach(function() {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('converts given AFF4 path to URL and returns server response', function() {
    $httpBackend.whenGET('/api/aff4/some/path').respond({foo: 'bar'});

    var response = grrAff4Service.get('aff4:/some/path');

    var responseData;
    response.then(function(data) { responseData = data.data });
    $httpBackend.flush();

    expect(responseData).toEqual({foo: 'bar'});
  });

  it('strips trailing slash from URN', function() {
    $httpBackend.whenGET('/api/aff4/some/path').respond(200);
    grrAff4Service.get('aff4:/some/path/');
    $httpBackend.flush();
  });

  it('uses grr.state.reason in requests', function() {
    grr.state.reason = 'some reason';

    $httpBackend.whenGET('/api/aff4/some/path?reason=some+reason').
        respond(200);
    grrAff4Service.get('aff4:/some/path');
    $httpBackend.flush();
  });

  it('passes user-provided headers in the request', function() {
    $httpBackend.whenGET('/api/aff4/some/path?key1=value1&key2=value2').
        respond(200);
    grrAff4Service.get('aff4:/some/path', {key1: 'value1', key2: 'value2'});
    $httpBackend.flush();
  });

  it('passes user-provided headers and reason in the request', function() {
    grr.state.reason = 'some reason';

    $httpBackend.whenGET('/api/aff4/some/path?' +
        'key1=value1&key2=value2&reason=some+reason').respond(200);
    grrAff4Service.get('aff4:/some/path', {key1: 'value1', key2: 'value2'});
    $httpBackend.flush();
  });

});
