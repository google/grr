'use strict';

goog.module('grrUi.core.globalNotificationsDirectiveTest');

const {GlobalNotificationsDirective} = goog.require('grrUi.core.globalNotificationsDirective');
const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {coreModule} = goog.require('grrUi.core.core');


describe('Global notifications directive', () => {
  let $compile;
  let $interval;
  let $q;
  let $rootScope;
  let grrApiService;


  const FETCH_INTERVAL = GlobalNotificationsDirective.fetch_interval;

  beforeEach(module('/static/angular-components/core/global-notifications.html'));
  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');
  }));

  const render = () => {
    const template = '<grr-global-notifications />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };

  const mockApiServiceResponse = (items) => {
    spyOn(grrApiService, 'get').and.callFake(() => $q.when({
      data: {items: items}
    }));
  };

  it('fetches pending gobal notifications and displays them', () => {
    const items = [{
      'value': {
        'content': {
          'value': 'Houston, Houston, we have a prob...',
        },
        'header': {
          'value': 'Oh no, we\'re doomed!',
        },
        'link': {
          'value': 'http://www.google.com',
        },
        'type': {
          'value': 'ERROR',
        },
      },
    }];
    mockApiServiceResponse(items);

    const element = render();
    $interval.flush(FETCH_INTERVAL);

    const url = 'users/me/notifications/pending/global';
    expect(grrApiService.get).toHaveBeenCalledWith(url);

    const alertElement = element.find('.alert.alert-error');
    expect(alertElement.length).toBe(1);
    expect(alertElement.find('h4').text().trim()).toBe('Oh no, we\'re doomed!');
    expect(alertElement.find('p').text().trim()).toBe('Houston, Houston, we have a prob...');
    expect(alertElement.find('a[href="http://www.google.com"]').length).toBe(1);
  });

  it('shows all notifications if multiple are returned', () => {
    const items = [
      {
        'value': {
          'content': {
            'value': 'Houston, Houston, we have a prob...',
          },
          'header': {
            'value': 'Oh no, we\'re doomed!',
          },
          'link': {
            'value': 'http://www.google.com',
          },
          'type': {
            'value': 'ERROR',
          },
        },
      },
      {
        'value': {
          'content': {
            'value': 'The word is nukular.',
          },
          'header': {
            'value': 'In case you didn\'t know!',
          },
          'type': {
            'value': 'INFO',
          },
        },
      }
    ];
    mockApiServiceResponse(items);

    const element = render();
    $interval.flush(FETCH_INTERVAL);

    const url = 'users/me/notifications/pending/global';
    expect(grrApiService.get).toHaveBeenCalledWith(url);

    const errorAlertElement = element.find('.alert.alert-error');
    expect(errorAlertElement.length).toBe(1);

    const infoAlertElement = element.find('.alert.alert-info');
    expect(infoAlertElement.length).toBe(1);
    expect(infoAlertElement.find('a').length).toBe(0);
  });

  it('deletes a notification when the close button is clicked', () => {
    const items = [{
      'value': {
        'content': {
          'value': 'The word is nukular.',
        },
        'header': {
          'value': 'In case you didn\'t know!',
        },
        'type': {
          'value': 'INFO',
        },
      },
    }];
    mockApiServiceResponse(items);
    spyOn(grrApiService, 'delete');

    const element = render();
    $interval.flush(FETCH_INTERVAL);

    browserTriggerEvent(element.find('button.close'), 'click');
    expect(grrApiService.delete).toHaveBeenCalledWith(
      'users/me/notifications/pending/global/INFO');
  });
});


exports = {};
