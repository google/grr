'use strict';

goog.require('grrUi.tests.module');
goog.require('grrUi.user.module');


describe('User label directive', function() {
  var $q, $compile, $rootScope, grrApiService;

  beforeEach(module(grrUi.user.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  var render = function(mockServerResponse) {
    // the directive uses grrApiService in the constructor already,
    // so either mock early or use $provide.
    mockApiServiceReponse(mockServerResponse);

    var template = '<grr-user-label />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };

  var mockApiServiceReponse = function(value){
    spyOn(grrApiService, 'getCached').and.callFake(function() {
      var deferred = $q.defer();
      deferred.resolve({
        data: {
          value: {
            username: {
              value: value
            }
          }
        }
      });
      return deferred.promise;
    });
  }

  it('fetches username and shows it', function() {
    var mockUserName = 'Test Username';
    var element = render(mockUserName);
    expect(grrApiService.getCached).toHaveBeenCalled();
    expect(element.text().trim()).toBe("User: " + mockUserName);
  });
});
