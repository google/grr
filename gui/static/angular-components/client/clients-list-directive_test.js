'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.module');

describe('clients list', function() {
  var $q, $compile, $rootScope, $interval, grrApiService, grrTimeService;
  var grrReflectionService;

  beforeEach(module('/static/angular-components/client/clients-list.html'));
  beforeEach(module('/static/angular-components/client/client-status-icons.html'));
  beforeEach(module('/static/angular-components/semantic/client-urn.html'));
  beforeEach(module('/static/angular-components/semantic/object-label.html'));
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');
    grrTimeService = $injector.get('grrTimeService');
    grrReflectionService = $injector.get('grrReflectionService');

    grrReflectionService.getRDFValueDescriptor = function(valueType) {
      var deferred = $q.defer();
      deferred.resolve({
        name: valueType,
        mro: [valueType]
      });
      return deferred.promise;
    };
  }));

  afterEach(function() {
    // We have to clean document's body to remove tables we add there.
    $(document.body).html('');
  });

  var render = function(query) {
    $rootScope.query = query;

    var template = '<grr-clients-list query="query" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    $('body').append(element);
    $interval.flush(1000);

    return element;
  };

  it('sends request with a query to the server', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var element = render('.');

    expect(grrApiService.get).toHaveBeenCalledWith(
        '/clients', {
          query: '.',
          offset: 0,
          count: 50
        });
  });

  it('renders list with one client correctly', function() {
    var clientsResponse = {
      items: [
        {
          aff4_class: 'VFSGRRClient',
          urn: 'aff4:/C.0000000000000001',
          attributes: {
            'metadata:hostname': {
              'value': 'localhost.com',
              'type': 'RDFString',
              'age': 1427300092
            },
            'metadata:os_version': {
              'value': '10.9.5',
              'type': 'VersionString',
              'age': 1427347403
            },
            'aff4:mac_addresses': {
              'value': '109add556715',
              'type': 'RDFString',
              'age': 1427347403
            },
            'aff4:user_names': {
              'value': 'user_foo user_bar',
              'type': 'SpaceSeparatedStringArray',
              'age': 1427347408
            },
            'metadata:FirstSeen': {
              'value': 1358346544915179,
              'type': 'RDFDatetime',
              'age': 1358346544
            },
            'metadata:install_date': {
              'value': 1385377629000000,
              'type': 'RDFDatetime',
              'age': 1427347403
            },
            'aff4:labels_list': {
              'value': {
                'labels': [
                  {
                    'value': {
                      'owner': {
                        'value': 'GRR',
                        'type': 'unicode',
                        'age': 0
                      },
                      'name': {
                        'value': 'foobar-label',
                        'type': 'unicode',
                        'age': 0
                      }
                    }
                  },
                ]
              },
              type: 'AFF4ObjectLabelsList'
            },
            'metadata:clock': {
              'value': 1427750098770803,
              'type': 'RDFDatetime',
              'age': 0
            }
          }
        }
      ]
    };

    var deferred = $q.defer();
    deferred.resolve({ data: clientsResponse });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var element = render('.');
    // Online/offline status icon.
    expect($('img[name=clientStatusIcon]', element).length).toBe(1);
    // Client id.
    expect(element.text()).toContain('C.0000000000000001');
    // Host name.
    expect(element.text()).toContain('localhost.com');
    // MAC address.
    expect(element.text()).toContain('109add556715');
    // OS version.
    expect(element.text()).toContain('10.9.5');
    // Usernames.
    expect(element.text()).toContain('user_foo');
    expect(element.text()).toContain('user_bar');
    // First seen.
    expect(element.text()).toContain('2013-01-16 14:29:04 UTC');
    // OS install date.
    expect(element.text()).toContain('2013-11-25 11:07:09 UTC');
    // Labels.
    expect(element.text()).toContain('foobar-label');
    // Last checkin.
    expect(element.text()).toContain('2015-03-30 21:14:58 UTC');
  });
});
