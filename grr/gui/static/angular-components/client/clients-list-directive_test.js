'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

describe('clients list', function() {
  var $q, $compile, $rootScope, $interval, grrApiService, grrRoutingService;
  var grrReflectionService;

  beforeEach(module('/static/angular-components/client/clients-list.html'));
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrClientStatusIcons');
  grrUi.tests.stubDirective('grrSemanticValue');
  grrUi.tests.stubDirective('grrDisableIfNoTrait');

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');
    grrReflectionService = $injector.get('grrReflectionService');
    grrRoutingService = $injector.get('grrRoutingService');

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
    var template = '<grr-clients-list />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    $('body').append(element);
    $interval.flush(1000);

    return element;
  };

  var mockApiService = function(value) {
    if (value) {
      spyOn(grrApiService, 'get').and.returnValue($q.when({ data: value }));
    } else {
      spyOn(grrApiService, 'get').and.returnValue($q.defer().promise);
    }
  };

  var mockRoutingService = function(query) {
    spyOn(grrRoutingService, 'uiOnParamsChanged').and.callFake(function(s, p, cb) {
      cb(query);
    });
  };

  it('sends request with a query to the server', function() {
    mockApiService();
    mockRoutingService('.');

    var element = render();
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
          type: 'VFSGRRClient',
          value: {
            urn: {
              value: 'aff4:/C.0000000000000001',
              type: 'RDFURN'
            },
            first_seen_at: {
              value: 1358346544915179,
              type: 'RDFDatetime',
            },
            last_clock: {
              value: 1427750098770803,
              type: 'RDFDatetime',
            },
            os_info: {
              value: {
                node: {
                  value: 'localhost.com',
                  type: 'RDFString',
                },
                version: {
                  value: '10.9.5',
                  type: 'VersionString',
                },
                install_date: {
                  value: 1385377629000000,
                  type: 'RDFDatetime',
                },
              },
              type: 'ClientInformation',
            },
            labels: [
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
            ],
            interfaces: [
              {
                type: 'Interface',
                value: {
                  mac_address: "<mac address>"
                }
              }
            ],
            users: [
              {
                type: 'User',
                value: {
                  username: {
                    type: 'RDFString',
                    value: 'user_foo',
                  }
                }
              },
              {
                type: 'User',
                value: {
                  type: 'RDFString',
                  value: 'user_bar',
                }
              }
            ]
          }
        }
      ]
    };

    mockApiService(clientsResponse);
    mockRoutingService('.');

    var element = render();
    // Check that grrClientStatusIcons directive is rendered. It means
    // that the row with a client info got rendered correctly.
    expect($('grr-client-status-icons', element).length).toBe(1);
  });

  it('ignores interfaces without mac addresses', function() {
    var clientsResponse = {
      items: [
        {
          type: 'VFSGRRClient',
          value: {
            urn: {
              value: 'aff4:/C.0000000000000001',
              type: 'RDFURN'
            },
            interfaces: [
              {
                type: 'Interface1',
                value: {
                  mac_address: "<mac address 1>"
                }
              },
              {
                type: 'Interface Without Mac Address',
                value: {
                }
              },
              {
                type: 'Interface2',
                value: {
                  mac_address: "<mac address 2>"
                }
              }
            ]
          }
        }
      ]
    };

    mockApiService(clientsResponse);
    mockRoutingService('.');

    var element = render();
    var macTableColumn = $('th:contains(MAC)', element).index();
    var macCell = $('tr td', element)[macTableColumn];
    var macDirective = $('grr-semantic-value', macCell);
    var macDirectiveScope = macDirective.scope();

    var addresses = macDirectiveScope.$eval(macDirective.attr('value'));
    expect(addresses).toEqual(['<mac address 1>', '<mac address 2>']);
  });
});
