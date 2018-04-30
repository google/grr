'use strict';

goog.module('grrUi.user.userNotificationButtonDirectiveTest');

const {UserNotificationButtonDirective} = goog.require('grrUi.user.userNotificationButtonDirective');
const {testsModule} = goog.require('grrUi.tests');
const {userModule} = goog.require('grrUi.user.user');


describe('User notification button directive', () => {
  let $compile;
  let $interval;
  let $q;
  let $rootScope;
  let grrApiService;


  const FETCH_INTERVAL = UserNotificationButtonDirective.fetch_interval;

  beforeEach(module('/static/angular-components/user/user-notification-button.html'));
  beforeEach(module(userModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');
  }));

  const render = () => {
    const template = '<grr-user-notification-button />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };

  const mockApiServiceResponse = (value) => {
    spyOn(grrApiService, 'get').and.callFake(() => {
      const deferred = $q.defer();
      deferred.resolve({ data: { count: value }});
      return deferred.promise;
    });
  };

  it('fetches pending notifications count and displays an info-styled button on 0',
     () => {
       mockApiServiceResponse(0);

       const element = render();
       $interval.flush(FETCH_INTERVAL);
       expect(grrApiService.get).toHaveBeenCalled();
       expect(element.text().trim()).toBe("0");
       expect(element.find('button').hasClass('btn-info')).toBe(true);
     });

  it('non-zero notifications count is shown as danger-styled button', () => {
    mockApiServiceResponse(5);

    const element = render();
    $interval.flush(FETCH_INTERVAL);
    expect(grrApiService.get).toHaveBeenCalled();
    expect(element.text().trim()).toBe("5");
    expect(element.find('button').hasClass('btn-danger')).toBe(true);
  });
});


exports = {};
