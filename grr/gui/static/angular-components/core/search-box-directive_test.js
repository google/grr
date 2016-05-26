'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubUiTrait');

var browserTrigger = grrUi.tests.browserTrigger;

describe('search box directive', function() {
  var $compile, $rootScope, $scope, $q, grrApiService, grrRoutingService;

  beforeEach(module('/static/angular-components/core/search-box.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubUiTrait('search_clients_action_enabled');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrRoutingService = $injector.get('grrRoutingService');
  }));

  var render = function() {
    var template = '<grr-search-box />';
    var element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  /**
   * Stubs out any calls to api service. By passing a dictionary of url-result pairs,
   * different server calls can be simulated. If no result for a given URL is found,
   * a failed server call will be simulated.
   */
  var mockApiServiceReponse = function(results) {
    results = results || {};
    spyOn(grrApiService, 'get').and.callFake(function(apiPath, params) {
      var value = results[apiPath];
      if (value) {
        return $q.resolve({ data: value });
      } else {
        return $q.reject('Invalid');
      }
    });
  };

  var triggerSearch = function(element, query) {
    $('input', element).val(query).trigger('input');
    browserTrigger($('input', element), 'change');
    browserTrigger($('button', element), 'click');
  };

  var triggerSearchByKeyboard = function(element, query) {
    element.find('input').val(query).trigger('input');
    $scope.$apply();

    // TODO(user): Use browserTriggerKeyDown when available.
    var event = jQuery.Event("keypress");
    event.which = 13;
    element.find('input').trigger(event);
  };

  it('should invoke client search on arbitrary input', function() {
    mockApiServiceReponse();
    spyOn(grrRoutingService, 'go');

    var element = render();
    triggerSearch(element, 'test query');

    expect(grrApiService.get).toHaveBeenCalledWith('/clients/labels');
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'test query'});
  });

  it('should invoke client search on ENTER in input', function() {
    mockApiServiceReponse();
    spyOn(grrRoutingService, 'go');

    var element = render();
    triggerSearchByKeyboard(element, 'test query');

    expect(grrApiService.get).toHaveBeenCalledWith('/clients/labels');
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'test query'});
  });

  it('should request hunt details if a hunt id is detected', function() {
    mockApiServiceReponse();

    var element = render();
    triggerSearch(element, 'H:12345678');
    expect(grrApiService.get).toHaveBeenCalledWith('hunts/H:12345678');
  });

  it('should forward to the hunt details if a hunt was found', function() {
    mockApiServiceReponse({
      'hunts/H:12345678': { urn: 'aff4:/H:12345678' }
    });
    spyOn(grrRoutingService, 'go');

    var element = render();
    triggerSearch(element, 'H:12345678');

    expect(grrApiService.get).toHaveBeenCalledWith('hunts/H:12345678');
    expect(grrRoutingService.go).toHaveBeenCalledWith('hunts', {huntId: 'H:12345678'});
  });

  it('should fall back to regular client search if no hunt was found', function() {
    mockApiServiceReponse(/* No param for HUNT url, so service call will be rejected. */);
    spyOn(grrRoutingService, 'go');

    var element = render();
    triggerSearch(element, 'H:12345678');

    expect(grrApiService.get).toHaveBeenCalledWith('hunts/H:12345678');
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'H:12345678'});
  });

  it('should check that potential hunt ids cannot start with search keywords', function() {
    mockApiServiceReponse();
    spyOn(grrRoutingService, 'go');

    var element = render();
    triggerSearch(element, 'HOST:12345678');
    triggerSearch(element, 'FQDN:12345678');
    triggerSearch(element, 'MAC:12345678');
    triggerSearch(element, 'IP:12345678');
    triggerSearch(element, 'USER:12345678');
    triggerSearch(element, 'LABEL:12345678');

    // None of the above calls should have triggered a hunt details call, since they are
    // all search keywords.
    expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {huntId: 'HOST:12345678'});
    expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {huntId: 'FQDN:12345678'});
    expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {huntId: 'MAC:12345678'});
    expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {huntId: 'IP:12345678'});
    expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {huntId: 'USER:12345678'});
    expect(grrRoutingService.go).not.toHaveBeenCalledWith('hunts', {huntId: 'LABEL:12345678'});

    // Instead, only client searches should have been issued.
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'HOST:12345678'});
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'FQDN:12345678'});
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'MAC:12345678'});
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'IP:12345678'});
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'USER:12345678'});
    expect(grrRoutingService.go).toHaveBeenCalledWith('search', {q: 'LABEL:12345678'});
  });

});
