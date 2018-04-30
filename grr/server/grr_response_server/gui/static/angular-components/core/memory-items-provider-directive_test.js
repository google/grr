'use strict';

goog.module('grrUi.core.memoryItemsProviderDirectiveTest');

const {MemoryItemsProviderController} = goog.require('grrUi.core.memoryItemsProviderDirective');


describe('memory items provider directive', () => {
  let $rootScope;

  beforeEach(inject(($injector) => {
    $rootScope = $injector.get('$rootScope');
  }));

  const getController = (testItems) => {
    $rootScope.testItems = testItems;

    let controller;
    inject(($injector) => {
      controller = $injector.instantiate(MemoryItemsProviderController, {
        '$scope': $rootScope,
        '$attrs': {
          'items': 'testItems',
        },
      });
    });
    $rootScope.$apply();

    return controller;
  };

  it('fetches ranges of elements according to offset and count', () => {
    const controller = getController([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    let items;

    controller.fetchItems(0, 10).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], offset: 0});

    controller.fetchItems(9, 1).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: [9], offset: 9});

    controller.fetchItems(9, 2).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: [9], offset: 9});
  });

  it('does not return total count when !opt_withTotalCount', () => {
    const controller = getController([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    let items;

    controller.fetchItems(9, 1).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items.totalCount).toBeUndefined();
  });

  it('returns total count when opt_withTotalCount is true', () => {
    const controller = getController([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    let items;

    controller.fetchItems(9, 1, true).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items.totalCount).toEqual(10);
  });

  it('fetches ranges of filtered strings', () => {
    const controller = getController(['foo', 'bar', 'foobar', 'barfoo']);
    let items;

    controller.fetchFilteredItems('foo', 0, 10).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: ['foo', 'foobar', 'barfoo'], offset: 0});

    controller.fetchFilteredItems('foo', 0, 1).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: ['foo'], offset: 0});

    controller.fetchFilteredItems('foo', 2, 1).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: ['barfoo'], offset: 2});
  });

  it('ignores case when filtering strings', () => {
    const controller = getController(['FOO', 'Bar', 'fooBar', 'barfoo']);
    let items;

    controller.fetchFilteredItems('foo', 0, 10).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: ['FOO', 'fooBar', 'barfoo'], offset: 0});

    controller.fetchFilteredItems('BAR', 0, 10).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: ['Bar', 'fooBar', 'barfoo'], offset: 0});
  });

  it('fetches ranges of filtered dictionaries', () => {
    const controller = getController([
      {message: 'foo'}, {message: 'bar'}, {message: 'foobar'},
      {message: 'barfoo'}
    ]);
    let items;

    controller.fetchFilteredItems('foo', 0, 10).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({
      items: [{message: 'foo'}, {message: 'foobar'}, {message: 'barfoo'}],
      offset: 0,
    });

    controller.fetchFilteredItems('foo', 0, 1).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: [{message: 'foo'}], offset: 0});

    controller.fetchFilteredItems('foo', 2, 1).then((resultItems) => {
      items = resultItems;
    });
    $rootScope.$apply();  // process promises
    expect(items).toEqual({items: [{message: 'barfoo'}], offset: 2});
  });
});


exports = {};
