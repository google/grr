'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.module');


describe('grr-check-client-access directive', function() {
  var $q, $compile, $rootScope, $timeout, grrApiService, grrRoutingService;

  beforeEach(module('/static/angular-components/client/' +
      'check-client-access.html'));
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $timeout = $injector.get('$timeout');

    grrApiService = $injector.get('grrApiService');
    grrRoutingService = $injector.get('grrRoutingService');
  }));

  var renderTestTemplate = function(noRedirect, omitClientId) {
    $rootScope.noRedirect = noRedirect;
    if (!omitClientId) {
      $rootScope.clientId = 'C.0001000200030004';
    }
    $rootScope.outHasAccess = undefined;

    var template = '<grr-check-client-access no-redirect="noRedirect" ' +
        'client-id="clientId" out-has-access="outHasAccess">foo-bar' +
        '</grr-check-client-access>';

    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('doesn\'t assign .access-disabled class when clientId is undefined', function() {
    spyOn(grrApiService, 'head').and.returnValue($q.defer().promise);

    var element = renderTestTemplate(false, true);
    expect(element.find('div.access-disabled').length).toBe(0);
  });

  it('shows transcluded content', function() {
    spyOn(grrApiService, 'head').and.returnValue($q.defer().promise);

    var element = renderTestTemplate();
    expect(element.text()).toContain('foo-bar');
  });

  it('sends HEAD request to check access', function() {
    spyOn(grrApiService, 'head').and.returnValue($q.defer().promise);

    var element = renderTestTemplate();
    expect(grrApiService.head).toHaveBeenCalledWith(
        'clients/C.0001000200030004/flows');
  });

  it('updates the "outHasAccess" binding when access is permitted', function() {
    var deferred = $q.defer();
    deferred.resolve();
    spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    expect($rootScope.outHasAccess).toBe(true);
  });

  it('doesn\'t assign .access-disabled class to container div when access is permitted', function() {
    var deferred = $q.defer();
    deferred.resolve();
    spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    expect(element.find('div.access-disabled').length).toBe(0);
  });

  it('updates the "outHasAccess" binding when access is rejected', function() {
    var deferred = $q.defer();
    deferred.reject();
    spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    expect($rootScope.outHasAccess).toBe(false);
  });

  it('assigns .access-disabled class to container div when access is rejected', function() {
    var deferred = $q.defer();
    deferred.reject();
    spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    expect(element.find('div.access-disabled').length).toBe(1);
  });

  it('redirects to "client" state after 1s if noRedirect!=true and access is rejected', function() {
    var deferred = $q.defer();
    deferred.reject();
    spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

    var element = renderTestTemplate();

    spyOn(grrRoutingService, 'go');
    $timeout.flush();
    expect(grrRoutingService.go).toHaveBeenCalledWith(
        'client', {clientId: 'C.0001000200030004'});
  });

  it('does not redirect after 1s if noRedirect=true and access is rejected', function() {
    var deferred = $q.defer();
    deferred.resolve();
    spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

    var element = renderTestTemplate();

    spyOn(grrRoutingService, 'go');
    $timeout.flush();
    expect(grrRoutingService.go).not.toHaveBeenCalled();
  });

});
