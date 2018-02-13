'use strict';

goog.module('grrUi.client.addClientsLabelsDialogDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {clientModule} = goog.require('grrUi.client.client');


describe('add clients labels dialog', () => {
  let $compile;
  let $q;
  let $rootScope;
  let closeSpy;
  let dismissSpy;
  let grrApiService;


  beforeEach(module('/static/angular-components/client/' +
      'add-clients-labels-dialog.html'));
  beforeEach(module('/static/angular-components/core/' +
      'confirmation-dialog.html'));
  // TODO(user): get rid of references to nested directives
  // templates in tests that do not test these nested directives. I.e. here
  // grr-client-urn directive is used and its template has to be
  // explicitly references in the test, although the test itself
  // is written for add-clients-labels-dialog directive.
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

  const renderTestTemplate = (clients) => {
    $rootScope.clients = clients;
    $rootScope.$close = closeSpy;
    $rootScope.$dismiss = dismissSpy;

    const template = '<grr-add-clients-labels-dialog ' +
        'clients="clients" />';

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows list of affected clients', () => {
    const element = renderTestTemplate(clients);
    expect(element.text()).toContain('C.0000111122223333');
    expect(element.text()).toContain('C.1111222233334444');
  });

  it('calls dismiss callback when "Cancel" is pressed', () => {
    const element = renderTestTemplate(clients);
    browserTriggerEvent($('button[name=Cancel]', element), 'click');

    expect(dismissSpy).toHaveBeenCalled();
  });

  it('disables Proceed if no label name is entered', () => {
    const element = renderTestTemplate(clients);
    expect($('input[name=labelBox]', element).val()).toEqual('');
    expect($('button[name=Proceed][disabled]', element).length).toBe(1);
  });

  it('enables Proceed if label name is entered', () => {
    const element = renderTestTemplate(clients);

    $('input[name=labelBox]', element).val('foobar');
    browserTriggerEvent($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();

    expect($('button[name=Proceed][disabled]', element).length).toBe(0);
  });

  it('sends request when Proceed is clicked', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    const element = renderTestTemplate(clients);

    $('input[name=labelBox]', element).val('foobar');
    browserTriggerEvent($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();

    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith('/clients/labels/add', {
      client_ids: ['C.0000111122223333', 'C.1111222233334444'],
      labels: ['foobar'],
    });
  });

  it('shows failure warning on failure', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    const element = renderTestTemplate(clients);
    $('input[name=labelBox]', element).val('foobar');
    browserTriggerEvent($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();
    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    deferred.reject({data: {message: 'NOT OK'}});
    $rootScope.$apply();

    expect(element.text()).toContain('NOT OK');
  });

  it('shows success message on success', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    const element = renderTestTemplate(clients);
    $('input[name=labelBox]', element).val('foobar');
    browserTriggerEvent($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();
    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    deferred.resolve('OK');
    $rootScope.$apply();

    expect(element.text()).toContain('Label was successfully added');
  });

  it('calls on-close callback when closed after success', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    const element = renderTestTemplate(clients);
    $('input[name=labelBox]', element).val('foobar');
    browserTriggerEvent($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();
    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    deferred.resolve('OK');
    $rootScope.$apply();

    browserTriggerEvent($('button[name=Close]', element), 'click');

    expect(closeSpy).toHaveBeenCalled();
  });
});


exports = {};
