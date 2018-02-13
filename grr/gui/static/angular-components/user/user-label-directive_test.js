'use strict';

goog.module('grrUi.user.userLabelDirectiveTest');

const {testsModule} = goog.require('grrUi.tests');
const {userModule} = goog.require('grrUi.user.user');


describe('User label directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module('/static/angular-components/user/user-label.html'));
  beforeEach(module(userModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  const render = () => {
    const template = '<grr-user-label />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };


  it('fetches username and shows it', () => {
    const mockUserName = 'Test Username';
    spyOn(grrApiService, 'getCached').and.callFake(() => {
      const deferred = $q.defer();
      deferred.resolve({
        data: {
          value: {
            username: {
              value: mockUserName,
            },
          },
        },
      });
      return deferred.promise;
    });

    const element = render(mockUserName);
    expect(element.text().trim()).toBe(`User: ${mockUserName}`);
  });

  it('shows special message in case of 403 error', () => {
    spyOn(grrApiService, 'getCached').and.callFake(() => {
      const deferred = $q.defer();
      deferred.reject({
        status: 403,
        statusText: 'Unauthorized',
      });
      return deferred.promise;
    });

    const element = render();
    expect(element.text().trim()).toBe('User: Authentication Error');
  });

  it('shows status text in case of a non-403 error', () => {
    spyOn(grrApiService, 'getCached').and.callFake(() => {
      const deferred = $q.defer();
      deferred.reject({
        status: 500,
        statusText: 'Error',
      });
      return deferred.promise;
    });

    const element = render();
    expect(element.text().trim()).toBe('User: Error');
  });
});


exports = {};
