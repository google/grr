'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('add clients labels dialog', function() {
  var $q, $compile, $rootScope, grrApiService, closeSpy, dismissSpy;

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
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');

    closeSpy = jasmine.createSpy('close');
    dismissSpy = jasmine.createSpy('dismiss');
  }));

  var clients = [
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'C.0000111122223333',
          type: 'RDFURN'
        }
      }
    },
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'C.1111222233334444',
          type: 'RDFURN'
        },
      }
    }
  ];

  var renderTestTemplate = function(clients) {
    $rootScope.clients = clients;
    $rootScope.$close = closeSpy;
    $rootScope.$dismiss = dismissSpy;

    var template = '<grr-add-clients-labels-dialog ' +
        'clients="clients" />';

    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows list of affected clients', function() {
    var element = renderTestTemplate(clients);
    expect(element.text()).toContain('C.0000111122223333');
    expect(element.text()).toContain('C.1111222233334444');
  });

  it('calls dismiss callback when "Cancel" is pressed', function() {
    var element = renderTestTemplate(clients);
    browserTrigger($('button[name=Cancel]', element), 'click');

    expect(dismissSpy).toHaveBeenCalled();
  });

  it('disables Proceed if no label name is entered', function() {
    var element = renderTestTemplate(clients);
    expect($('input[name=labelBox]', element).val()).toEqual('');
    expect($('button[name=Proceed][disabled]', element).length).toBe(1);
  });

  it('enables Proceed if label name is entered', function() {
    var element = renderTestTemplate(clients);

    $('input[name=labelBox]', element).val('foobar');
    browserTrigger($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();

    expect($('button[name=Proceed][disabled]', element).length).toBe(0);
  });

  it('sends request when Proceed is clicked', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    var element = renderTestTemplate(clients);

    $('input[name=labelBox]', element).val('foobar');
    browserTrigger($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();

    browserTrigger($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith(
        '/clients/labels/add',
        {
          client_ids: ['C.0000111122223333', 'C.1111222233334444'],
          labels: ['foobar']
        });
  });

  it('shows failure warning on failure', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    var element = renderTestTemplate(clients);
    $('input[name=labelBox]', element).val('foobar');
    browserTrigger($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();
    browserTrigger($('button[name=Proceed]', element), 'click');

    deferred.reject({data: {message: 'NOT OK'}});
    $rootScope.$apply();

    expect(element.text()).toContain('NOT OK');
  });

  it('shows success message on success', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    var element = renderTestTemplate(clients);
    $('input[name=labelBox]', element).val('foobar');
    browserTrigger($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();
    browserTrigger($('button[name=Proceed]', element), 'click');

    deferred.resolve('OK');
    $rootScope.$apply();

    expect(element.text()).toContain('Label was successfully added');
  });

  it('calls on-close callback when closed after success', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    var element = renderTestTemplate(clients);
    $('input[name=labelBox]', element).val('foobar');
    browserTrigger($('input[name=labelBox]', element), 'change');
    $rootScope.$apply();
    browserTrigger($('button[name=Proceed]', element), 'click');

    deferred.resolve('OK');
    $rootScope.$apply();

    browserTrigger($('button[name=Close]', element), 'click');

    expect(closeSpy).toHaveBeenCalled();
  });
});
