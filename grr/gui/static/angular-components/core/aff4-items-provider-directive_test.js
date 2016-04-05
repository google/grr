'use strict';

goog.require('grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderController');
goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');


describe('AFF4 items provider directive', function() {
  var $q, $compile, $rootScope, grrAff4ServiceMock;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    grrAff4ServiceMock = {get: function() {}};
  }));

  var getController = function(aff4Path, queryParams, transformItems,
                               testResponse) {
    var controller;

    $rootScope.testAff4Path = aff4Path;
    $rootScope.testQueryParams = queryParams;
    $rootScope.testTransformItems = transformItems;

    inject(function($injector) {
      controller = $injector.instantiate(
          grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderController,
          {
            '$scope': $rootScope,
            '$attrs': {
              'aff4Path': 'testAff4Path',
              'queryParams': 'testQueryParams',
              'transformItems': transformItems ?
                  'testTransformItems(items)' : undefined
            },
            'grrAff4Service': grrAff4ServiceMock
          });
    });

    var deferred = $q.defer();
    deferred.resolve(testResponse);
    spyOn(grrAff4ServiceMock, 'get').and.returnValue(deferred.promise);

    $rootScope.$apply();

    return controller;
  };

  it('fetches ranges of elements according to offset and count', function() {
    var controller = getController(
        'aff4:/foo/bar', undefined, undefined);

    controller.fetchItems(0, 10);
    expect(grrAff4ServiceMock.get).toHaveBeenCalledWith(
        'aff4:/foo/bar',
        {
          'RDFValueCollection.offset': 0,
          'RDFValueCollection.count': 10,
          'RDFValueCollection.with_total_count': 0
        });
  });

  it('does not fetch/return total count when !opt_withTotalCount', function() {
    var controller = getController(
        'aff4:/foo/bar', undefined, undefined,
        {
          data: {
            items: []
          }
        });
    var items;

    controller.fetchItems(0, 10, false).then(function(resultItems) {
      items = resultItems;
    });
    expect(grrAff4ServiceMock.get).toHaveBeenCalledWith(
        'aff4:/foo/bar',
        {
          'RDFValueCollection.offset': 0,
          'RDFValueCollection.count': 10,
          'RDFValueCollection.with_total_count': 0
        });

    $rootScope.$apply();
    expect(items.totalCount).toBeUndefined();
  });

  it('fetches/returns total count when opt_withTotalCount is true', function() {
    var controller = getController(
        'aff4:/foo/bar', undefined, undefined,
        {
          data: {
            items: [],
            total_count: 42
          }
        });
    var items;

    controller.fetchItems(0, 10, true).then(function(resultItems) {
      items = resultItems;
    });
    expect(grrAff4ServiceMock.get).toHaveBeenCalledWith(
        'aff4:/foo/bar',
        {
          'RDFValueCollection.offset': 0,
          'RDFValueCollection.count': 10,
          'RDFValueCollection.with_total_count': 1
        });

    $rootScope.$apply();
    expect(items.totalCount).toEqual(42);
  });

  it('fetches filtered data if filter is specified', function() {
    var controller = getController(
        'aff4:/foo/bar', undefined, undefined);

    controller.fetchFilteredItems('foo', 0, 10);
    expect(grrAff4ServiceMock.get).toHaveBeenCalledWith(
        'aff4:/foo/bar',
        {
          'RDFValueCollection.offset': 0,
          'RDFValueCollection.count': 10,
          'RDFValueCollection.filter': 'foo'
        });
  });

  it('passes additional parameters as query params when fetching', function() {
    var controller = getController(
        'aff4:/foo/bar', {foo: 'bar', num: 42}, undefined);

    controller.fetchItems(0, 10);
    expect(grrAff4ServiceMock.get).toHaveBeenCalledWith(
        'aff4:/foo/bar',
        {
          'RDFValueCollection.offset': 0,
          'RDFValueCollection.count': 10,
          'RDFValueCollection.with_total_count': 0,
          num: 42,
          foo: 'bar'
        });
  });

  it('passes additional parameters when fetching filtered', function() {
    var controller = getController(
        'aff4:/foo/bar', {foo: 'bar', num: 42}, undefined);

    controller.fetchFilteredItems('foo', 0, 10);
    expect(grrAff4ServiceMock.get).toHaveBeenCalledWith(
        'aff4:/foo/bar',
        {
          'RDFValueCollection.offset': 0,
          'RDFValueCollection.count': 10,
          'RDFValueCollection.filter': 'foo',
          num: 42,
          foo: 'bar'
        });
  });

  it('offset/count/withTotalCount override queryParams attributes', function() {
    var controller = getController(
        'aff4:/foo/bar',
        {
          foo: 'bar',
          num: 42,
          'RDFValueCollection.offset': 2,
          'RDFValueCollection.count': 3,
          'RDFValueCollection.with_total_count': 0
        },
        undefined);

    controller.fetchItems(0, 10, true);
    expect(grrAff4ServiceMock.get).toHaveBeenCalledWith(
        'aff4:/foo/bar',
        {
          'RDFValueCollection.offset': 0,
          'RDFValueCollection.count': 10,
          'RDFValueCollection.with_total_count': 1,
          num: 42,
          foo: 'bar'
        });
  });

  it('transforms resulting data with transform function', function() {
    var transformItems = function(items) {
      expect(items).toEqual([1, 2, 3, 4, 5]);
      for (var i = 0; i < items.length; ++i) {
        items[i]++;
      }
      return items;
    };

    var controller = getController(
        'aff4:/foo/bar', undefined, transformItems,
        {
          data: {
            items: [1, 2, 3, 4, 5]
          }
        });

    var items;
    controller.fetchItems(0, 10, true).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();
    expect(items).toEqual({items: [2, 3, 4, 5, 6], offset: undefined});
  });

  it('throws if transform function returns nothing', function() {
    var transformItems = function(items) {
    };

    var controller = getController(
        'aff4:/foo/bar', undefined, transformItems,
        {
          data: {
            items: []
          }
        });

    expect(function() {
      controller.fetchItems(0, 10, true).then(function(unusedResultItems) {
      });
      $rootScope.$apply();
    }).toThrow(Error('transform-items function returned undefined'));
  });
});
