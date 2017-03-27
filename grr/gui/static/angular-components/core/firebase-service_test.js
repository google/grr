'use strict';

goog.require('grrUi.core.module');


var firebase = firebase || {};


describe('API service', function() {
  var $rootScope, $http, $q, grrApiService, grrFirebaseService;
  var fbAuthResult, redirectDeferred;

  beforeEach(module(grrUi.core.module.name));

  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
    $http = $injector.get('$http');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrFirebaseService = $injector.get('grrFirebaseService');

    redirectDeferred = $q.defer();

    fbAuthResult = {
      getRedirectResult: jasmine.createSpy('getRedirectResult').and
          .returnValue(redirectDeferred.promise),
      onAuthStateChanged: jasmine.createSpy('onAuthStateChanged'),
      signInWithRedirect: jasmine.createSpy('signInWithRedirect')
    };
    firebase = {
      auth: jasmine.createSpy('auth').and.returnValue(fbAuthResult),
      apps: [{
        options: {
          authProvider: "GoogleAuthProvider"
        }
      }]
    };
    firebase.auth.GoogleAuthProvider = jasmine.createSpy('GoogleAuthProvider');

  }));

  it('does nothing and marks auth done on no firebase apps', function() {
    firebase.apps = [];

    spyOn(grrApiService, 'markAuthDone');

    grrFirebaseService.setupIfNeeded();
    $rootScope.$apply();

    expect(firebase.auth).not.toHaveBeenCalled();
    expect(grrApiService.markAuthDone).toHaveBeenCalled();
  });

  it('adjusts headers and marks auth done when user authenticates', function() {
    var tokenDeferred = $q.defer();
    tokenDeferred.resolve('blah');
    var user = {
      getToken: jasmine.createSpy('getToken').and
          .returnValue(tokenDeferred.promise)
    };
    fbAuthResult.onAuthStateChanged.and.callFake(function(fn) {
      fn(user);
    });
    spyOn(grrApiService, 'markAuthDone');

    grrFirebaseService.setupIfNeeded();
    $rootScope.$apply();

    expect(fbAuthResult.onAuthStateChanged).toHaveBeenCalled();
    expect(fbAuthResult.signInWithRedirect).not.toHaveBeenCalled();
    expect(grrApiService.markAuthDone).toHaveBeenCalled();

    expect($http.defaults.headers['common']['Authorization'])
        .toBe('Bearer blah');
  });

  it('redirects to sign-in flow if the user is not authenticated', function() {
    fbAuthResult.onAuthStateChanged.and.callFake(function(fn) {
      fn(undefined);
    });
    spyOn(grrApiService, 'markAuthDone');

    grrFirebaseService.setupIfNeeded();
    $rootScope.$apply();

    expect(fbAuthResult.onAuthStateChanged).toHaveBeenCalled();
    expect(fbAuthResult.signInWithRedirect).toHaveBeenCalled();
    expect(grrApiService.markAuthDone).not.toHaveBeenCalled();
  });

  it('marks auth done and does not redirect again on auth error', function() {
    var redirectDeferred = $q.defer();
    redirectDeferred.reject('blah');
    fbAuthResult.getRedirectResult.and.returnValue(redirectDeferred.promise);

    spyOn(grrApiService, 'markAuthDone');

    grrFirebaseService.setupIfNeeded();
    $rootScope.$apply();

    expect(grrApiService.markAuthDone).toHaveBeenCalled();
    expect(fbAuthResult.signInWithRedirect).not.toHaveBeenCalled();
  });
});
