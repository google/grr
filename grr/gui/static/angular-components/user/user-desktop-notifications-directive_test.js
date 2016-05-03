'use strict';

goog.require('grrUi.tests.module');
goog.require('grrUi.user.module');
goog.require('grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective');


describe('User desktop notifications directive', function() {
  var $q, $compile, $rootScope, $interval, $window, grrApiService;

  var FETCH_INTERVAL =
      grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective.fetch_interval;

  beforeEach(module(grrUi.user.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(function() {
    $window = {
      location: {
        replace: jasmine.createSpy(),
        reload: jasmine.createSpy()
      },
      focus: jasmine.createSpy()
    };

    module(function($provide) {
      $provide.value('$window', $window);
    });
  });

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');

    window.Notification = function () {
      this.close = function () {};
    };
    spyOn(window, 'Notification').and.callThrough();
  }));

  var render = function() {
    var template = '<grr-user-desktop-notifications />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };

  var mockApiServiceResponse = function(value){
    spyOn(grrApiService, 'get').and.callFake(function() {
      var deferred = $q.defer();
      deferred.resolve({data: {items: value}});
      return deferred.promise;
    });
  };

  it('fetches a single pending notification and displays it as a desktop ' +
     'notification', function() {
    mockApiServiceResponse(
        [{'type': 'ApiNotification',
          'value': {
            'is_pending': {'type': 'RDFBool', 'value': true},
            'message': {
              'type': 'unicode',
              'value': 'Host-0: <some message>'
            },
            'reference': {
              'type': 'ApiNotificationReference',
              'value': {
                'discovery': {
                  'type': 'ApiNotificationDiscoveryReference',
                  'value': {
                    'client_id': {
                      'type': 'ClientURN',
                      'value': 'aff4:/C.1000000000000000'
                }}},
                'type': {
                  'type': 'EnumNamedValue',
                  'value': 'DISCOVERY'
                }
            }},
            'timestamp': {'type': 'RDFDatetime', 'value': 42000000}
         }}]);

    var element = render();
    $interval.flush(FETCH_INTERVAL);

    expect(grrApiService.get).toHaveBeenCalled();

    expect(Notification.calls.count()).toBe(1);

    expect(Notification).toHaveBeenCalledWith(
        'GRR', {'body': 'Host-0: <some message>',
                'icon': 'static/images/grr_logo_notification.png',
                'tag': 'GRR42000000'});
  });

  it('provides a relevant onclick callback for the desktop notification',
      function() {
    mockApiServiceResponse(
        [{'type': 'ApiNotification',
          'value': {
            'is_pending': {'type': 'RDFBool', 'value': true},
            'message': {
              'type': 'unicode',
              'value': 'Host-0: <some message>'
            },
            'reference': {
              'type': 'ApiNotificationReference',
              'value': {
                'discovery': {
                  'type': 'ApiNotificationDiscoveryReference',
                  'value': {
                    'client_id': {
                      'type': 'ClientURN',
                      'value': 'aff4:/C.1000000000000000'
                }}},
                'type': {
                  'type': 'EnumNamedValue',
                  'value': 'DISCOVERY'
                }
            }},
            'timestamp': {'type': 'RDFDatetime', 'value': 42000000}
         }}]);

    spyOn(grrApiService, 'delete');

    var element = render();
    $interval.flush(FETCH_INTERVAL);

    Notification.calls.mostRecent().object.onclick();

    expect(grrApiService.delete).toHaveBeenCalledWith(
        'users/me/notifications/pending/42000000');

    expect($window.location.href).toContain(
        encodeURIComponent('aff4:/C.1000000000000000'));
    expect($window.location.reload).toHaveBeenCalled();
  });

  it('fetches pending notifications and displays the last two of them as ' +
     'desktop notifications', function() {
    mockApiServiceResponse(
        [{'type': 'ApiNotification',
          'value': {
            'is_pending': {'type': 'RDFBool', 'value': true},
            'message': {'type': 'unicode',
                        'value': 'Host-0: <another message>'},
            'reference': {
              'type': 'ApiNotificationReference',
              'value': {
                'type': {'type': 'EnumNamedValue', 'value': 'VFS'},
                'vfs': {
                  'type': 'ApiNotificationVfsReference',
                  'value': {
                    'client_id': {
                      'type': 'ClientURN',
                      'value': 'aff4:/C.1000000000000000'
                    },
                    'vfs_path': {
                      'type': 'RDFURN',
                      'value': 'aff4:/C.1000000000000000'
            }}}}},
            'timestamp': {'type': 'RDFDatetime', 'value': 48000000}
         }},
         {'type': 'ApiNotification',
          'value': {
            'is_pending': {'type': 'RDFBool', 'value': true},
            'message': {
              'type': 'unicode',
              'value': 'Host-0: <some message>'
            },
            'reference': {
              'type': 'ApiNotificationReference',
              'value': {
                'discovery': {
                  'type': 'ApiNotificationDiscoveryReference',
                  'value': {
                    'client_id': {
                      'type': 'ClientURN',
                      'value': 'aff4:/C.1000000000000000'
                }}},
                'type': {
                  'type': 'EnumNamedValue',
                  'value': 'DISCOVERY'
                }
            }},
            'timestamp': {'type': 'RDFDatetime', 'value': 42000000}
         }},
         {'type': 'ApiNotification',
          'value': {
            'is_pending': {'type': 'RDFBool', 'value': true},
            'message': {'type': 'unicode',
                        'value': 'Host-0: <some other message>'},
            'reference': {
              'type': 'ApiNotificationReference',
              'value': {
                'type': {'type': 'EnumNamedValue', 'value': 'VFS'},
                'vfs': {
                  'type': 'ApiNotificationVfsReference',
                  'value': {
                    'client_id': {
                      'type': 'ClientURN',
                      'value': 'aff4:/C.1000000000000000'
                    },
                    'vfs_path': {
                      'type': 'RDFURN',
                      'value': 'aff4:/C.1000000000000000'
            }}}}},
            'timestamp': {'type': 'RDFDatetime', 'value': 44000000}
         }}]);

    var element = render();
    $interval.flush(FETCH_INTERVAL);

    expect(grrApiService.get).toHaveBeenCalled();

    expect(Notification.calls.count()).toBe(2);

    var firstCallArgs = Notification.calls.all()[0]['args'];
    var secondCallArgs = Notification.calls.all()[1]['args'];

    expect(firstCallArgs).toEqual(
        ['GRR', {'body': 'Host-0: <some other message>',
                 'icon': 'static/images/grr_logo_notification.png',
                 'tag': 'GRR44000000'}]);

    expect(secondCallArgs).toEqual(
        ['GRR', {'body': 'Host-0: <another message>',
                 'icon': 'static/images/grr_logo_notification.png',
                 'tag': 'GRR48000000'}]);
  });
});
