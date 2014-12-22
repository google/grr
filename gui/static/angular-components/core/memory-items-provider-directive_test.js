'use strict';

goog.require('grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderController');


describe('memory items provider directive', function() {
  var $q, $rootScope;

  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
  }));

  var getController = function(testItems) {
    $rootScope.testItems = testItems;

    var controller;
    inject(function($injector) {
      controller = $injector.instantiate(
          grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderController,
          {
            '$scope': $rootScope,
            '$attrs': {
              'items': 'testItems'
            }
          });
    });
    $rootScope.$apply();

    return controller;
  };

  it('fetches ranges of elements according to offset and count', function() {
    var controller = getController([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    var items;

    controller.fetchItems(0, 10).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);

    controller.fetchItems(9, 1).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual([9]);

    controller.fetchItems(9, 2).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual([9]);
  });

  it('does not return total count when !opt_withTotalCount', function() {
    var controller = getController([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    var items;

    controller.fetchItems(9, 1).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items.totalCount).toBeUndefined();
  });

  it('returns total count when opt_withTotalCount is true', function() {
    var controller = getController([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    var items;

    controller.fetchItems(9, 1, true).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items.totalCount).toEqual(10);
  });

  it('fetches ranges of filtered strings', function() {
    var controller = getController(['foo', 'bar', 'foobar', 'barfoo']);
    var items;

    controller.fetchFilteredItems('foo', 0, 10).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual(['foo', 'foobar', 'barfoo']);

    controller.fetchFilteredItems('foo', 0, 1).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual(['foo']);

    controller.fetchFilteredItems('foo', 2, 1).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual(['barfoo']);
  });

  it('fetches ranges of filtered dictionaries', function() {
    var controller = getController([{message: 'foo'},
                                    {message: 'bar'},
                                    {message: 'foobar'},
                                    {message: 'barfoo'}]);
    var items;

    controller.fetchFilteredItems('foo', 0, 10).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual([{message: 'foo'},
                           {message: 'foobar'},
                           {message: 'barfoo'}]);

    controller.fetchFilteredItems('foo', 0, 1).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual([{message: 'foo'}]);

    controller.fetchFilteredItems('foo', 2, 1).then(function(resultItems) {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual([{message: 'barfoo'}]);
  });
});
