'use strict';

goog.require('grrUi.tests.module');
goog.require('grrUi.user.module');


describe('User desktop notifications directive', function() {
  var $q, $compile, $rootScope, $interval, grrApiService;

  var FETCH_INTERVAL = 10000;

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
    var template = '<grr-user-desktop-notifications />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };

  var mockApiServiceResponse = function(value){
    spyOn(grrApiService, 'get').and.callFake(function() {
      var deferred = $q.defer();
      deferred.resolve({ data: { items: value }});
      return deferred.promise;
    });
  };

  beforeEach(function() { spyOn(window, 'Notification'); });

  it('fetches a single pending notifications and displays it as a desktop ' +
     'notification', function() {
    mockApiServiceResponse(
        [{"type": "ApiNotification",
          "value": {
            "is_pending": {"type": "RDFBool", "value": true},
            "message": {
              "type": "unicode",
              "value": "Host-0: <some message>"
            },
            "reference": {
              "type": "ApiNotificationReference",
              "value": {
                "discovery": {
                  "type": "ApiNotificationDiscoveryReference",
                  "value": {
                    "client_id": {
                      "type": "ClientURN",
                      "value": "aff4:/C.1000000000000000"
                }}},
                "type": {
                  "type": "EnumNamedValue",
                  "value": "DISCOVERY"
                }
            }},
            "timestamp": {"type": "RDFDatetime", "value": 42000000}
         }}]);

    var element = render();
    $interval.flush(FETCH_INTERVAL);

    expect(grrApiService.get).toHaveBeenCalled();

    expect(Notification.calls.count()).toBe(1);

    expect(Notification).toHaveBeenCalledWith(
        "GRR", {"icon": "static/images/grr_logo_notification.png",
                "body": "Host-0: <some message>"});
  });

  it('fetches pending notifications and displays the last two of them as ' +
     'desktop notifications', function() {
    mockApiServiceResponse(
        [{"type": "ApiNotification",
          "value": {
            "is_pending": {"type": "RDFBool", "value": true},
            "message": {"type": "unicode",
                        "value": "Host-0: <another message>"},
            "reference": {
              "type": "ApiNotificationReference",
              "value": {
                "type": {"type": "EnumNamedValue", "value": "VFS"},
                "vfs": {
                  "type": "ApiNotificationVfsReference",
                  "value": {
                    "client_id": {
                      "type": "ClientURN",
                      "value": "aff4:/C.1000000000000000"
                    },
                    "vfs_path": {
                      "type": "RDFURN",
                      "value": "aff4:/C.1000000000000000"
            }}}}},
            "timestamp": {"type": "RDFDatetime", "value": 48000000}
         }},
         {"type": "ApiNotification",
          "value": {
            "is_pending": {"type": "RDFBool", "value": true},
            "message": {
              "type": "unicode",
              "value": "Host-0: <some message>"
            },
            "reference": {
              "type": "ApiNotificationReference",
              "value": {
                "discovery": {
                  "type": "ApiNotificationDiscoveryReference",
                  "value": {
                    "client_id": {
                      "type": "ClientURN",
                      "value": "aff4:/C.1000000000000000"
                }}},
                "type": {
                  "type": "EnumNamedValue",
                  "value": "DISCOVERY"
                }
            }},
            "timestamp": {"type": "RDFDatetime", "value": 42000000}
         }},
         {"type": "ApiNotification",
          "value": {
            "is_pending": {"type": "RDFBool", "value": true},
            "message": {"type": "unicode",
                        "value": "Host-0: <some other message>"},
            "reference": {
              "type": "ApiNotificationReference",
              "value": {
                "type": {"type": "EnumNamedValue", "value": "VFS"},
                "vfs": {
                  "type": "ApiNotificationVfsReference",
                  "value": {
                    "client_id": {
                      "type": "ClientURN",
                      "value": "aff4:/C.1000000000000000"
                    },
                    "vfs_path": {
                      "type": "RDFURN",
                      "value": "aff4:/C.1000000000000000"
            }}}}},
            "timestamp": {"type": "RDFDatetime", "value": 44000000}
         }}]);

    var element = render();
    $interval.flush(FETCH_INTERVAL);

    expect(grrApiService.get).toHaveBeenCalled();

    expect(Notification.calls.count()).toBe(2);

    var firstCallArgs = Notification.calls.all()[0]['args'];
    var secondCallArgs = Notification.calls.all()[1]['args'];

    expect(firstCallArgs).toEqual(
        ["GRR", {"icon": "static/images/grr_logo_notification.png",
                 "body": "Host-0: <some other message>"}]);

    expect(secondCallArgs).toEqual(
        ["GRR", {"icon": "static/images/grr_logo_notification.png",
                 "body":"Host-0: <another message>"}]);
  });
});
