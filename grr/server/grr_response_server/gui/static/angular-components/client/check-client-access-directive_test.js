'use strict';

goog.module('grrUi.client.checkClientAccessDirectiveTest');

const {clientModule} = goog.require('grrUi.client.client');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-check-client-access directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let $timeout;
  let grrApiService;
  let grrRoutingService;


  beforeEach(module('/static/angular-components/client/' +
      'check-client-access.html'));
  beforeEach(module(clientModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $timeout = $injector.get('$timeout');

    grrApiService = $injector.get('grrApiService');
    grrRoutingService = $injector.get('grrRoutingService');
  }));

  const renderTestTemplate = (noRedirect, omitClientId) => {
    $rootScope.noRedirect = noRedirect;
    if (!omitClientId) {
      $rootScope.clientId = 'C.0001000200030004';
    }
    $rootScope.outHasAccess = undefined;

    const template = '<grr-check-client-access no-redirect="noRedirect" ' +
        'client-id="clientId" out-has-access="outHasAccess">foo-bar' +
        '</grr-check-client-access>';

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('doesn\'t assign .access-disabled class when clientId is undefined',
     () => {
       spyOn(grrApiService, 'head').and.returnValue($q.defer().promise);

       const element = renderTestTemplate(false, true);
       expect(element.find('div.access-disabled').length).toBe(0);
     });

  it('shows transcluded content', () => {
    spyOn(grrApiService, 'head').and.returnValue($q.defer().promise);

    const element = renderTestTemplate();
    expect(element.text()).toContain('foo-bar');
  });

  it('sends HEAD request to check access', () => {
    spyOn(grrApiService, 'head').and.returnValue($q.defer().promise);

    renderTestTemplate();
    expect(grrApiService.head).toHaveBeenCalledWith(
        'clients/C.0001000200030004/flows');
  });

  it('updates the "outHasAccess" binding when access is permitted', () => {
    const deferred = $q.defer();
    deferred.resolve();
    spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

    renderTestTemplate();
    expect($rootScope.outHasAccess).toBe(true);
  });

  it('doesn\'t assign .access-disabled class to container div when access is permitted',
     () => {
       const deferred = $q.defer();
       deferred.resolve();
       spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

       const element = renderTestTemplate();
       expect(element.find('div.access-disabled').length).toBe(0);
     });

  it('updates the "outHasAccess" binding when access is rejected', () => {
    const deferred = $q.defer();
    deferred.reject();
    spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

    renderTestTemplate();
    expect($rootScope.outHasAccess).toBe(false);
  });

  it('assigns .access-disabled class to container div when access is rejected',
     () => {
       const deferred = $q.defer();
       deferred.reject();
       spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

       const element = renderTestTemplate();
       expect(element.find('div.access-disabled').length).toBe(1);
     });

  it('redirects to "client" state after 1s if noRedirect!=true and access is rejected',
     () => {
       const deferred = $q.defer();
       deferred.reject();
       spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

       renderTestTemplate();

       spyOn(grrRoutingService, 'go');
       $timeout.flush();
       expect(grrRoutingService.go).toHaveBeenCalledWith('client', {
         clientId: 'C.0001000200030004'
       });
     });

  it('does not redirect after 1s if noRedirect=true and access is rejected',
     () => {
       const deferred = $q.defer();
       deferred.resolve();
       spyOn(grrApiService, 'head').and.returnValue(deferred.promise);

       renderTestTemplate();

       spyOn(grrRoutingService, 'go');
       $timeout.flush();
       expect(grrRoutingService.go).not.toHaveBeenCalled();
     });
});


exports = {};
