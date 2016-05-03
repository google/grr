'use strict';

goog.require('grrUi.tests.module');
goog.require('grrUi.user.module');
goog.require('grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective');


describe('User notification button directive', function() {
  var $q, $compile, $rootScope, $interval, grrApiService;

  var FETCH_INTERVAL =
      grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective.fetch_interval;

  beforeEach(module('/static/angular-components/user/user-notification-button.html'));
  beforeEach(module(grrUi.user.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');
  }));

  var render = function() {
    var template = '<grr-user-notification-button />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };

  var mockApiServiceResponse = function(value){
    spyOn(grrApiService, 'get').and.callFake(function() {
      var deferred = $q.defer();
      deferred.resolve({ data: { count: value }});
      return deferred.promise;
    });
  };

  it('fetches pending notifications count and displays an info-styled button on 0', function() {
    mockApiServiceResponse(0);

    var element = render();
    $interval.flush(FETCH_INTERVAL);
    expect(grrApiService.get).toHaveBeenCalled();
    expect(element.text().trim()).toBe("0");
    expect(element.find('button').hasClass('btn-info')).toBe(true);
  });

  it('non-zero notifications count is shown as danger-styled button', function() {
    mockApiServiceResponse(5);

    var element = render();
    $interval.flush(FETCH_INTERVAL);
    expect(grrApiService.get).toHaveBeenCalled();
    expect(element.text().trim()).toBe("5");
    expect(element.find('button').hasClass('btn-danger')).toBe(true);
  });
});
