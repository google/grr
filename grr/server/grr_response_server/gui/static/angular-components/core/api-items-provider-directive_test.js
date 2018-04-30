'use strict';

goog.module('grrUi.core.apiItemsProviderDirectiveTest');

const {ApiItemsProviderController} = goog.require('grrUi.core.apiItemsProviderDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('API items provider directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiServiceMock;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    grrApiServiceMock = {get: function() {}};
  }));

  const getController = (url, queryParams, transformItems, testResponse) => {
    let controller;

    $rootScope.testUrl = url;
    $rootScope.testQueryParams = queryParams;
    $rootScope.testTransformItems = transformItems;

    inject(($injector) => {
      controller = $injector.instantiate(ApiItemsProviderController, {
        '$scope': $rootScope,
        '$attrs': {
          'url': 'testUrl',
          'queryParams': 'testQueryParams',
          'transformItems': transformItems ? 'testTransformItems(items)' :
                                             undefined,
        },
        'grrApiService': grrApiServiceMock,
      });
    });

    const deferred = $q.defer();
    deferred.resolve(testResponse);
    spyOn(grrApiServiceMock, 'get').and.returnValue(deferred.promise);

    $rootScope.$apply();

    return controller;
  };

  it('fetches ranges of items according to offset and count', () => {
    const controller = getController('some/api/path', undefined, undefined);

    controller.fetchItems(0, 10);
    expect(grrApiServiceMock.get).toHaveBeenCalledWith(
        'some/api/path', {offset: 0, count: 10});
  });

  it('does not fetch total count when opt_withTotalCount is true', () => {
    const controller = getController('some/api/path', undefined, undefined);

    controller.fetchItems(0, 10, true);
    expect(grrApiServiceMock.get).toHaveBeenCalledWith(
        'some/api/path', {offset: 0, count: 10});
  });

  it('adds "filter" to query when fetching filtered items', () => {
    const controller = getController('some/api/path', undefined, undefined);

    controller.fetchFilteredItems('some', 0, 10);
    expect(grrApiServiceMock.get).toHaveBeenCalledWith(
        'some/api/path', {offset: 0, count: 10, filter: 'some'});
  });
});


exports = {};
