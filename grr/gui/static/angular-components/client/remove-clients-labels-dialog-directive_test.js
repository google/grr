'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('remove clients labels dialog', function() {
  var $q, $compile, $rootScope, grrApiService, closeSpy, dismissSpy;

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

  var renderTestTemplate = function(clients) {
    $rootScope.clients = clients;
    $rootScope.$close = closeSpy;
    $rootScope.$dismiss = dismissSpy;

    var template = '<grr-remove-clients-labels-dialog ' +
        'clients="clients" />';

    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows list of affected clients', function() {
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
    var element = renderTestTemplate(clients);
    expect(element.text()).toContain('C.0000111122223333');
    expect(element.text()).toContain('C.1111222233334444');
  });

  var clientsWithTwoUserLabels = [
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'C.0000111122223333',
          type: 'RDFURN'
        },
        labels: [
          {
            value: {
              name: {
                value: 'foo',
              },
              owner: {
                value: 'test2'
              }
            }
          }
        ]
      }
    },
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'C.1111222233334444',
          type: 'RDFURN'
        },
        labels: [
          {
            value: {
              name: {
                value: 'bar',
              },
              owner: {
                value: 'test2'
              }
            }
          }
        ]
      }
    }
  ];

  var clientsWithOneUserLabelAndOneSystemLabel = [
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'C.0000111122223333',
          type: 'RDFURN'
        },
        labels: [
          {
            value: {
              name: {
                value: 'foo',
              },
              owner: {
                value: 'GRR'
              }
            }
          }
        ]
      }
    },
    {
      type: 'ApiClient',
      value: {
        urn: {
          value: 'C.1111222233334444',
          type: 'RDFURN'
        },
        labels: [
          {
            value: {
              name: {
                value: 'bar',
              },
              owner: {
                value: 'test2'
              }
            }
          }
        ]
      }
    }
  ];

  it('shows dropdown with a union of labels from all clients', function() {
    var element = renderTestTemplate(clientsWithTwoUserLabels);
    expect($('select option', element).length).toBe(2);
    expect($('select option[label=foo]', element).length).toBe(1);
    expect($('select option[label=bar]', element).length).toBe(1);
  });

  it('does not show system labels in the list', function() {
    var element = renderTestTemplate(clientsWithOneUserLabelAndOneSystemLabel);
    expect($('select option', element).length).toBe(1);
    expect($('select option[label=foo]', element).length).toBe(0);
    expect($('select option[label=bar]', element).length).toBe(1);
  });

  it('has a label selected by default', function() {
    var element = renderTestTemplate(clientsWithTwoUserLabels);
    var selected = $(':selected', element).text();
    expect(selected).toBeDefined();
  });

  it('calls dismiss callback when "Cancel" is pressed', function() {
    var element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTrigger($('button[name=Cancel]', element), 'click');

    expect(dismissSpy).toHaveBeenCalled();
  });

  it('sends request when proceed is clicked', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    var element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTrigger($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith(
        '/clients/labels/remove',
        {
          client_ids: ['C.0000111122223333', 'C.1111222233334444'],
          labels: ['foo']
        });
  });

  it('shows failure warning on failure', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    var element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTrigger($('button[name=Proceed]', element), 'click');

    deferred.reject({data: {message: 'NOT OK'}});
    $rootScope.$apply();

    expect(element.text()).toContain('NOT OK');
  });

  it('shows success message on success', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    var element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTrigger($('button[name=Proceed]', element), 'click');

    deferred.resolve('OK');
    $rootScope.$apply();

    expect(element.text()).toContain('Label was successfully removed');
  });

  it('calls on-close callback when closed after success', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    var element = renderTestTemplate(clientsWithTwoUserLabels);
    browserTrigger($('button[name=Proceed]', element), 'click');

    deferred.resolve('OK');
    $rootScope.$apply();

    browserTrigger($('button[name=Close]', element), 'click');

    expect(closeSpy).toHaveBeenCalled();
  });

});
