'use strict';

goog.require('grrUi.core.globalNotificationsDirective.GlobalNotificationsDirective');
goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('Global notifications directive', function() {
  var $q, $compile, $rootScope, $interval, grrApiService;

  var FETCH_INTERVAL =
      grrUi.core.globalNotificationsDirective.GlobalNotificationsDirective.fetch_interval;

  beforeEach(module('/static/angular-components/core/global-notifications.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');
  }));

  var render = function() {
    var template = '<grr-global-notifications />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };

  var mockApiServiceResponse = function(items){
    spyOn(grrApiService, 'get').and.callFake(function() {
      return $q.when({ data: { items: items }});
    });
  };

  it('fetches pending gobal notifications and displays them', function() {
    var items = [{
      "value": {
        "content": {
          "value": "Houston, Houston, we have a prob..."
        },
        "header": {
          "value": "Oh no, we're doomed!"
        },
        "link": {
          "value": "http://www.google.com"
        },
        "type": {
          "value": "ERROR"
        }
      }
    }];
    mockApiServiceResponse(items);

    var element = render();
    $interval.flush(FETCH_INTERVAL);

    var url = 'users/me/notifications/pending/global';
    expect(grrApiService.get).toHaveBeenCalledWith(url);

    var alertElement = element.find('.alert.alert-error');
    expect(alertElement.length).toBe(1);
    expect(alertElement.find('h4').text().trim()).toBe('Oh no, we\'re doomed!');
    expect(alertElement.find('p').text().trim()).toBe('Houston, Houston, we have a prob...');
    expect(alertElement.find('a[href="http://www.google.com"]').length).toBe(1);
  });

  it('shows all notifications if multiple are returned', function() {
    var items = [{
      "value": {
        "content": {
          "value": "Houston, Houston, we have a prob..."
        },
        "header": {
          "value": "Oh no, we're doomed!"
        },
        "link": {
          "value": "http://www.google.com"
        },
        "type": {
          "value": "ERROR"
        }
      }
    }, {
      "value": {
        "content": {
          "value": "The word is nukular."
        },
        "header": {
          "value": "In case you didn't know!"
        },
        "type": {
          "value": "INFO"
        }
      }
    }];
    mockApiServiceResponse(items);

    var element = render();
    $interval.flush(FETCH_INTERVAL);

    var url = 'users/me/notifications/pending/global';
    expect(grrApiService.get).toHaveBeenCalledWith(url);

    var errorAlertElement = element.find('.alert.alert-error');
    expect(errorAlertElement.length).toBe(1);

    var infoAlertElement = element.find('.alert.alert-info');
    expect(infoAlertElement.length).toBe(1);
    expect(infoAlertElement.find('a').length).toBe(0);
  });

  it('deletes a notification when the close button is clicked', function() {
    var items = [{
      "value": {
        "content": {
          "value": "The word is nukular."
        },
        "header": {
          "value": "In case you didn't know!"
        },
        "type": {
          "value": "INFO"
        }
      }
    }];
    mockApiServiceResponse(items);
    spyOn(grrApiService, 'delete');

    var element = render();
    $interval.flush(FETCH_INTERVAL);

    browserTrigger(element.find('button.close'), 'click');
    expect(grrApiService.delete).toHaveBeenCalledWith(
      'users/me/notifications/pending/global/INFO');
  });
});
