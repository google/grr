'use strict';

goog.module('grrUi.core.searchBoxDirectiveTest');

const {browserTriggerEvent, stubUiTrait, testsModule} = goog.require('grrUi.tests');
const {coreModule} = goog.require('grrUi.core.core');


describe('search box directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let $scope;
  let grrApiService;
  let grrRoutingService;


  beforeEach(module('/static/angular-components/core/search-box.html'));
  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  stubUiTrait('search_clients_action_enabled');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrRoutingService = $injector.get('grrRoutingService');
  }));

  const render = () => {
    const template = '<grr-search-box />';
    const element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  /**
   * Stubs out any calls to api service. By passing a dictionary of url-result pairs,
   * different server calls can be simulated. If no result for a given URL is found,
   * a failed server call will be simulated.
   */
  const mockApiServiceResponse = (results) => {
    results = results || {};
    spyOn(grrApiService, 'get').and.callFake((apiPath, params) => {
      const value = results[apiPath];
      if (value) {
        return $q.resolve({ data: value });
      } else {
        return $q.reject('Invalid');
      }
    });
  };

  const triggerSearch = (element, query) => {
    $('input', element).val(query).trigger('input');
    browserTriggerEvent($('input', element), 'change');
    browserTriggerEvent($('button', element), 'click');
  };

  const triggerSearchByKeyboard = (element, query) => {
    element.find('input').val(query).trigger('input');
    $scope.$apply();

    // TODO(user): Use browserTriggerKeyDown when available.
    const event = jQuery.Event('keypress');
    event.which = 13;
    element.find('input').trigger(event);
  };

  it('should invoke client search on arbitrary input', () => {
    mockApiServiceResponse();
    spyOn(grrRoutingService, 'go');

    const element = render();
    triggerSearch(element, 'test query');

    expect(grrApiService.get).toHaveBeenCalledWith('/clients/labels');
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'test query'});
  });

  it('should invoke client search on ENTER in input', () => {
    mockApiServiceResponse();
    spyOn(grrRoutingService, 'go');

    const element = render();
    triggerSearchByKeyboard(element, 'test query');

    expect(grrApiService.get).toHaveBeenCalledWith('/clients/labels');
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'test query'});
  });

  it('should request hunt details if a hunt id is detected', () => {
    mockApiServiceResponse();

    const element = render();
    triggerSearch(element, 'H:12345678');
    expect(grrApiService.get).toHaveBeenCalledWith('hunts/H:12345678');
  });

  it('should forward to the hunt details if a hunt was found', () => {
    mockApiServiceResponse({
      'hunts/H:12345678': {
        value: {
          hunt_id: {
            value: 'H:12345678',
          },
        },
      },
    });
    spyOn(grrRoutingService, 'go');

    const element = render();
    triggerSearch(element, 'H:12345678');

    expect(grrApiService.get).toHaveBeenCalledWith('hunts/H:12345678');
    expect(grrRoutingService.go).toHaveBeenCalledWith('hunts', {huntId: 'H:12345678'});
  });

  it('should fall back to regular client search if no hunt was found', () => {
    mockApiServiceResponse(/* No param for HUNT url, so service call will be rejected. */);
    spyOn(grrRoutingService, 'go');

    const element = render();
    triggerSearch(element, 'H:12345678');

    expect(grrApiService.get).toHaveBeenCalledWith('hunts/H:12345678');
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'H:12345678'});
  });

  it('should check that potential hunt ids cannot start with search keywords',
     () => {
       mockApiServiceResponse();
       spyOn(grrRoutingService, 'go');

       const element = render();
       triggerSearch(element, 'HOST:12345678');
       triggerSearch(element, 'FQDN:12345678');
       triggerSearch(element, 'MAC:12345678');
       triggerSearch(element, 'IP:12345678');
       triggerSearch(element, 'USER:12345678');
       triggerSearch(element, 'LABEL:12345678');

       // None of the above calls should have triggered a hunt details call,
       // since they are all search keywords.
       expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {
         huntId: 'HOST:12345678'
       });
       expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {
         huntId: 'FQDN:12345678'
       });
       expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {
         huntId: 'MAC:12345678'
       });
       expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {
         huntId: 'IP:12345678'
       });
       expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {
         huntId: 'USER:12345678'
       });
       expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {
         huntId: 'LABEL:12345678'
       });

       // Instead, only client searches should have been issued.
       expect(grrRoutingService.go).toHaveBeenCalledWith('search', {
         q: 'HOST:12345678'
       });
       expect(grrRoutingService.go).toHaveBeenCalledWith('search', {
         q: 'FQDN:12345678'
       });
       expect(grrRoutingService.go).toHaveBeenCalledWith('search', {
         q: 'MAC:12345678'
       });
       expect(grrRoutingService.go).toHaveBeenCalledWith('search', {
         q: 'IP:12345678'
       });
       expect(grrRoutingService.go).toHaveBeenCalledWith('search', {
         q: 'USER:12345678'
       });
       expect(grrRoutingService.go).toHaveBeenCalledWith('search', {
         q: 'LABEL:12345678'
       });
     });
});


exports = {};
