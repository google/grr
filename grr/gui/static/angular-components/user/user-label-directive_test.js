'use strict';

goog.require('grrUi.tests.module');
goog.require('grrUi.user.module');


describe('User label directive', function() {
  var $q, $compile, $rootScope, grrApiService;

  beforeEach(module('/static/angular-components/user/user-label.html'));
  beforeEach(module(grrUi.user.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  var render = function() {
    var template = '<grr-user-label />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };


  it('fetches username and shows it', function() {
    var mockUserName = 'Test Username';
    spyOn(grrApiService, 'getCached').and.callFake(function() {
      var deferred = $q.defer();
      deferred.resolve({
        data: {
          value: {
            username: {
              value: mockUserName
            }
          }
        }
      });
      return deferred.promise;
    });

    var element = render(mockUserName);
    expect(element.text().trim()).toBe('User: ' + mockUserName);
  });

  it('shows special message in case of 403 error', function() {
    spyOn(grrApiService, 'getCached').and.callFake(function() {
      var deferred = $q.defer();
      deferred.reject({
        status: 403,
        statusText: 'Unauthorized'
      });
      return deferred.promise;
    });

    var element = render();
    expect(element.text().trim()).toBe('User: Authentication Error');
  });

  it('shows status text in case of a non-403 error', function() {
    spyOn(grrApiService, 'getCached').and.callFake(function() {
      var deferred = $q.defer();
      deferred.reject({
        status: 500,
        statusText: 'Error'
      });
      return deferred.promise;
    });

    var element = render();
    expect(element.text().trim()).toBe('User: Error');
  });
});
