'use strict';

goog.module('grrUi.client.clientsListDirectiveTest');

const {clientModule} = goog.require('grrUi.client.client');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('clients list', () => {
  let $compile;
  let $interval;
  let $q;
  let $rootScope;
  let grrApiService;
  let grrRoutingService;

  let grrReflectionService;

  beforeEach(module('/static/angular-components/client/clients-list.html'));
  beforeEach(module(clientModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrClientStatusIcons');
  stubDirective('grrSemanticValue');
  stubDirective('grrDisableIfNoTrait');

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    grrApiService = $injector.get('grrApiService');
    grrReflectionService = $injector.get('grrReflectionService');
    grrRoutingService = $injector.get('grrRoutingService');

    grrReflectionService.getRDFValueDescriptor = ((valueType) => {
      const deferred = $q.defer();
      deferred.resolve({
        name: valueType,
        mro: [valueType],
      });
      return deferred.promise;
    });
  }));

  afterEach(() => {
    // We have to clean document's body to remove tables we add there.
    $(document.body).html('');
  });

  const render = (query) => {
    const template = '<grr-clients-list />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    $('body').append(element);
    $interval.flush(1000);

    return element;
  };

  const mockApiService = (value) => {
    if (value) {
      // Be able to handle 2 requests: second request will be made if less
      // then 1 page of items is returned.
      spyOn(grrApiService, 'get').and.returnValues($q.when({ data: value }),
                                                   $q.defer().promise);
    } else {
      spyOn(grrApiService, 'get').and.returnValue($q.defer().promise);
    }
  };

  const mockRoutingService = (query) => {
    spyOn(grrRoutingService, 'uiOnParamsChanged').and.callFake((s, p, cb) => {
      cb(query);
    });
  };

  it('sends request with a query to the server', () => {
    mockApiService();
    mockRoutingService('.');

    render();
    expect(grrApiService.get).toHaveBeenCalledWith('/clients', {
      query: '.',
      offset: 0,
      count: 50,
    });
  });

  it('renders list with one client correctly', () => {
    const clientsResponse = {
      items: [
        {
          type: 'VFSGRRClient',
          value: {
            client_id: {
              value: 'C.0000000000000001',
              type: 'ApiClientId',
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
                fqdn: {
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
                    'age': 0,
                  },
                  'name': {
                    'value': 'foobar-label',
                    'type': 'unicode',
                    'age': 0,
                  },
                },
              },
            ],
            interfaces: [
              {
                type: 'Interface',
                value: {
                  mac_address: '<mac address>',
                },
              },
            ],
            users: [
              {
                type: 'User',
                value: {
                  username: {
                    type: 'RDFString',
                    value: 'user_foo',
                  },
                },
              },
              {
                type: 'User',
                value: {
                  type: 'RDFString',
                  value: 'user_bar',
                },
              },
            ],
          },
        },
      ],
    };

    mockApiService(clientsResponse);
    mockRoutingService('.');

    const element = render();
    // Check that grrClientStatusIcons directive is rendered. It means
    // that the row with a client info got rendered correctly.
    expect($('grr-client-status-icons', element).length).toBe(1);
  });

  it('ignores interfaces without mac addresses', () => {
    const clientsResponse = {
      items: [
        {
          type: 'VFSGRRClient',
          value: {
            client_id: {
              value: 'C.0000000000000001',
              type: 'ApiClientId',
            },
            interfaces: [
              {
                type: 'Interface1',
                value: {
                  mac_address: '<mac address 1>',
                },
              },
              {
                type: 'Interface Without Mac Address',
                value: {},
              },
              {
                type: 'Interface2',
                value: {
                  mac_address: '<mac address 2>',
                },
              },
            ],
          },
        },
      ],
    };

    mockApiService(clientsResponse);
    mockRoutingService('.');

    const element = render();
    const macTableColumn = $('th:contains(MAC)', element).index();
    const macCell = $('tr td', element)[macTableColumn];
    const macDirective = $('grr-semantic-value', macCell);
    const macDirectiveScope = macDirective.scope();

    const addresses = macDirectiveScope.$eval(macDirective.attr('value'));
    expect(addresses).toEqual(['<mac address 1>', '<mac address 2>']);
  });
});


exports = {};
