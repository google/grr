'use strict';

goog.module('grrUi.user.userDesktopNotificationsDirectiveTest');

const {UserNotificationButtonDirective} = goog.require('grrUi.user.userNotificationButtonDirective');
const {testsModule} = goog.require('grrUi.tests');
const {userModule} = goog.require('grrUi.user.user');


describe('User desktop notifications directive', () => {
  let $compile;
  let $interval;
  let $q;
  let $rootScope;
  let $location;
  let grrApiService;


  const FETCH_INTERVAL = UserNotificationButtonDirective.fetch_interval;

  beforeEach(module(userModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $location = $injector.get('$location');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');

    window.Notification = function() {
      this.close = (() => {});
    };
    spyOn(window, 'Notification').and.callThrough();
  }));

  const render = () => {
    const template = '<grr-user-desktop-notifications />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();
    return element;
  };

  const mockApiServiceResponse = (value) => {
    spyOn(grrApiService, 'get').and.callFake(() => {
      const deferred = $q.defer();
      deferred.resolve({data: {items: value}});
      return deferred.promise;
    });
  };

  it('fetches a single pending notification and displays it as a desktop ' +
         'notification',
     () => {
       mockApiServiceResponse([{
         'type': 'ApiNotification',
         'value': {
           'is_pending': {'type': 'RDFBool', 'value': true},
           'message': {
             'type': 'unicode',
             'value': 'Host-0: <some message>',
           },
           'reference': {
             'type': 'ApiNotificationReference',
             'value': {
               'discovery': {
                 'type': 'ApiNotificationDiscoveryReference',
                 'value': {
                   'client_id': {
                     'type': 'ClientURN',
                     'value': 'aff4:/C.1000000000000000',
                   }
                 }
               },
               'type': {
                 'type': 'EnumNamedValue',
                 'value': 'DISCOVERY',
               },
             }
           },
           'timestamp': {'type': 'RDFDatetime', 'value': 42000000},
         }
       }]);

       render();
       $interval.flush(FETCH_INTERVAL);

       expect(grrApiService.get).toHaveBeenCalled();

       expect(Notification.calls.count()).toBe(1);

       expect(Notification).toHaveBeenCalledWith('GRR', {
         'body': 'Host-0: <some message>',
         'icon': 'static/images/grr_logo_notification.png',
         'tag': 'GRR42000000'
       });
     });

  it('provides a relevant onclick callback for the desktop notification',
     () => {
       mockApiServiceResponse([{
         'type': 'ApiNotification',
         'value': {
           'is_pending': {'type': 'RDFBool', 'value': true},
           'message': {
             'type': 'unicode',
             'value': 'Host-0: <some message>',
           },
           'reference': {
             'type': 'ApiNotificationReference',
             'value': {
               'discovery': {
                 'type': 'ApiNotificationDiscoveryReference',
                 'value': {
                   'client_id': {
                     'type': 'ClientURN',
                     'value': 'aff4:/C.1000000000000000',
                   }
                 }
               },
               'type': {
                 'type': 'EnumNamedValue',
                 'value': 'DISCOVERY',
               },
             }
           },
           'timestamp': {'type': 'RDFDatetime', 'value': 42000000},
         }
       }]);

       spyOn(grrApiService, 'delete');
       spyOn($location, 'path');

       render();
       $interval.flush(FETCH_INTERVAL);

       Notification.calls.mostRecent().object.onclick();

       expect(grrApiService.delete)
           .toHaveBeenCalledWith('users/me/notifications/pending/42000000');

       expect($location.path).toHaveBeenCalledWith('clients/C.1000000000000000');
     });

  it('fetches pending notifications and displays the last two of them as ' +
         'desktop notifications',
     () => {
       mockApiServiceResponse([
         {
           'type': 'ApiNotification',
           'value': {
             'is_pending': {'type': 'RDFBool', 'value': true},
             'message':
                 {'type': 'unicode', 'value': 'Host-0: <another message>'},
             'reference': {
               'type': 'ApiNotificationReference',
               'value': {
                 'type': {'type': 'EnumNamedValue', 'value': 'VFS'},
                 'vfs': {
                   'type': 'ApiNotificationVfsReference',
                   'value': {
                     'client_id': {
                       'type': 'ClientURN',
                       'value': 'aff4:/C.1000000000000000',
                     },
                     'vfs_path': {
                       'type': 'RDFURN',
                       'value': 'aff4:/C.1000000000000000',
                     }
                   }
                 }
               }
             },
             'timestamp': {'type': 'RDFDatetime', 'value': 48000000},
           }
         },
         {
           'type': 'ApiNotification',
           'value': {
             'is_pending': {'type': 'RDFBool', 'value': true},
             'message': {
               'type': 'unicode',
               'value': 'Host-0: <some message>',
             },
             'reference': {
               'type': 'ApiNotificationReference',
               'value': {
                 'discovery': {
                   'type': 'ApiNotificationDiscoveryReference',
                   'value': {
                     'client_id': {
                       'type': 'ClientURN',
                       'value': 'aff4:/C.1000000000000000',
                     }
                   }
                 },
                 'type': {
                   'type': 'EnumNamedValue',
                   'value': 'DISCOVERY',
                 },
               }
             },
             'timestamp': {'type': 'RDFDatetime', 'value': 42000000},
           }
         },
         {
           'type': 'ApiNotification',
           'value': {
             'is_pending': {'type': 'RDFBool', 'value': true},
             'message':
                 {'type': 'unicode', 'value': 'Host-0: <some other message>'},
             'reference': {
               'type': 'ApiNotificationReference',
               'value': {
                 'type': {'type': 'EnumNamedValue', 'value': 'VFS'},
                 'vfs': {
                   'type': 'ApiNotificationVfsReference',
                   'value': {
                     'client_id': {
                       'type': 'ClientURN',
                       'value': 'aff4:/C.1000000000000000',
                     },
                     'vfs_path': {
                       'type': 'RDFURN',
                       'value': 'aff4:/C.1000000000000000',
                     }
                   }
                 }
               }
             },
             'timestamp': {'type': 'RDFDatetime', 'value': 44000000},
           }
         }
       ]);

       render();
       $interval.flush(FETCH_INTERVAL);

       expect(grrApiService.get).toHaveBeenCalled();

       expect(Notification.calls.count()).toBe(2);

       const firstCallArgs = Notification.calls.all()[0]['args'];
       const secondCallArgs = Notification.calls.all()[1]['args'];

       expect(firstCallArgs).toEqual([
         'GRR', {
           'body': 'Host-0: <some other message>',
           'icon': 'static/images/grr_logo_notification.png',
           'tag': 'GRR44000000'
         }
       ]);

       expect(secondCallArgs).toEqual([
         'GRR', {
           'body': 'Host-0: <another message>',
           'icon': 'static/images/grr_logo_notification.png',
           'tag': 'GRR48000000'
         }
       ]);
     });
});


exports = {};
