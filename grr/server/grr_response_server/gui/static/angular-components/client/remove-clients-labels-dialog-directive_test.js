'use strict';

goog.module('grrUi.client.removeClientsLabelsDialogDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {clientModule} = goog.require('grrUi.client.client');


describe('remove clients labels dialog', () => {
  let $compile;
  let $q;
  let $rootScope;
  let closeSpy;
  let dismissSpy;
  let grrApiService;


  beforeEach(module('/static/angular-components/client/' +
      'remove-clients-labels-dialog.html'));
  beforeEach(module('/static/angular-components/core/' +
      'confirmation-dialog.html'));
  // TODO(user): get rid of references to nested directives
  // templates in tests that do not test these nested directives. I.e. here
  // grr-client-urn directive is used and its template has to be
  // explicitly references in the test, although the test itself
  // is written for remove-clients-labels-dialog directive.
  beforeEach(module('/static/angular-components/semantic/' +
      'client-urn.html'));
  beforeEach(module(clientModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');

    closeSpy = jasmine.createSpy('close');
    dismissSpy = jasmine.createSpy('dismiss');
  }));

  const renderTestTemplate = (clients) => {
    $rootScope.clients = clients;
    $rootScope.$close = closeSpy;
    $rootScope.$dismiss = dismissSpy;

    const template = '<grr-remove-clients-labels-dialog ' +
        'clients="clients" />';

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows list of affected clients', () => {
    const clients = [
      {
        type: 'ApiClient',
        value: {
          urn: {
            value: 'aff4:/C.0000111122223333',
            type: 'RDFURN',
          },
          client_id: {
            value: 'C.0000111122223333',
            type: 'ApiClientId',
          },
        },
      },
      {
        type: 'ApiClient',
        value: {
          urn: {
            value: 'aff4:/C.1111222233334444',
            type: 'RDFURN',
          },
          client_id: {
            value: 'C.1111222233334444',
            type: 'ApiClientId',
          },
        },
      },
    ];
    const element = renderTestTemplate(clients);
    expect(element.text()).toContain('C.0000111122223333');
    expect(element.text()).toContain('C.1111222233334444');
  });

  const clientsWithTwoUserLabels = [
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'aff4:/C.0000111122223333',
          type: 'RDFURN',
        },
        client_id: {
          value: 'C.0000111122223333',
          type: 'ApiClientId',
        },
        labels: [
          {
            value: {
              name: {
                value: 'foo',
              },
              owner: {
                value: 'test2',
              },
            },
          },
        ],
      },
    },
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'aff4:/C.1111222233334444',
          type: 'RDFURN',
        },
        client_id: {
          value: 'C.1111222233334444',
          type: 'ApiClientId',
        },
        labels: [
          {
            value: {
              name: {
                value: 'bar',
              },
              owner: {
                value: 'test2',
              },
            },
          },
        ],
      },
    },
  ];

  const clientsWithOneUserLabelAndOneSystemLabel = [
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'aff4:/C.0000111122223333',
          type: 'RDFURN',
        },
        client_id: {
          value: 'C.0000111122223333',
          type: 'ApiClientId',
        },
        labels: [
          {
            value: {
              name: {
                value: 'foo',
              },
              owner: {
                value: 'GRR',
              },
            },
          },
        ],
      },
    },
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'aff4:/C.1111222233334444',
          type: 'RDFURN',
        },
        client_id: {
          value: 'C.1111222233334444',
          type: 'ApiClientId',
        },
        labels: [
          {
            value: {
              name: {
                value: 'bar',
              },
              owner: {
                value: 'test2',
              },
            },
          },
        ],
      },
    },
  ];

  it('shows dropdown with a union of labels from all clients', () => {
    const element = renderTestTemplate(clientsWithTwoUserLabels);
    expect($('select option', element).length).toBe(2);
    expect($('select option[label=foo]', element).length).toBe(1);
    expect($('select option[label=bar]', element).length).toBe(1);
  });

  it('does not show system labels in the list', () => {
    const element =
        renderTestTemplate(clientsWithOneUserLabelAndOneSystemLabel);
    expect($('select option', element).length).toBe(1);
    expect($('select option[label=foo]', element).length).toBe(0);
    expect($('select option[label=bar]', element).length).toBe(1);
  });

  it('has a label selected by default', () => {
    const element = renderTestTemplate(clientsWithTwoUserLabels);
    const selected = $(':selected', element).text();
    expect(selected).toBeDefined();
  });

  it('calls dismiss callback when "Cancel" is pressed', () => {
    const element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTriggerEvent($('button[name=Cancel]', element), 'click');

    expect(dismissSpy).toHaveBeenCalled();
  });

  it('sends request when proceed is clicked', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    const element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith('/clients/labels/remove', {
      client_ids: ['C.0000111122223333', 'C.1111222233334444'],
      labels: ['foo'],
    });
  });

  it('shows failure warning on failure', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    const element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    deferred.reject({data: {message: 'NOT OK'}});
    $rootScope.$apply();

    expect(element.text()).toContain('NOT OK');
  });

  it('shows success message on success', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    const element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    deferred.resolve('OK');
    $rootScope.$apply();

    expect(element.text()).toContain('Label was successfully removed');
  });

  it('calls on-close callback when closed after success', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    const element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    deferred.resolve('OK');
    $rootScope.$apply();

    browserTriggerEvent($('button[name=Close]', element), 'click');

    expect(closeSpy).toHaveBeenCalled();
  });
});


exports = {};
