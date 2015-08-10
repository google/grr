'use strict';

goog.require('grrUi.core.apiItemsProviderDirective.ApiItemsProviderController');
goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');


describe('API items provider directive', function() {
  var $q, $compile, $rootScope, grrApiServiceMock;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    grrApiServiceMock = {get: function() {}};
  }));

  var getController = function(url, queryParams, transformItems,
                               testResponse) {
    var controller;

    $rootScope.testUrl = url;
    $rootScope.testQueryParams = queryParams;
    $rootScope.testTransformItems = transformItems;

    inject(function($injector) {
      controller = $injector.instantiate(
          grrUi.core.apiItemsProviderDirective.ApiItemsProviderController,
          {
            '$scope': $rootScope,
            '$attrs': {
              'url': 'testUrl',
              'queryParams': 'testQueryParams',
              'transformItems': transformItems ?
                  'testTransformItems(items)' : undefined
            },
            'grrApiService': grrApiServiceMock
          });
    });

    var deferred = $q.defer();
    deferred.resolve(testResponse);
    spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

    $rootScope.$apply();

    return controller;
  };

  it('fetches ranges of items according to offset and count', function() {
    var controller = getController(
        'some/api/path', undefined, undefined);

    controller.fetchItems(0, 10);
    expect(grrApiServiceMock.get).toHaveBeenCalledWith(
        'some/api/path', {offset: 0, count: 10});
  });

  it('does not fetch total count when opt_withTotalCount is true', function() {
    var controller = getController(
        'some/api/path', undefined, undefined);

    controller.fetchItems(0, 10, true);
    expect(grrApiServiceMock.get).toHaveBeenCalledWith(
        'some/api/path', {offset: 0, count: 10});
  });

  it('adds "filter" to query when fetching filtered items', function() {
    var controller = getController(
        'some/api/path', undefined, undefined);

    controller.fetchFilteredItems('some', 0, 10);
    expect(grrApiServiceMock.get).toHaveBeenCalledWith(
        'some/api/path', {offset: 0, count: 10, filter: 'some'});
  });
});
