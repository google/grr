'use strict';

goog.module('grrUi.core.pagedFilteredTableDirectiveTest');

const {MemoryItemsProviderController} = goog.require('grrUi.core.memoryItemsProviderDirective');
const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {coreModule} = goog.require('grrUi.core.core');


describe('paged filtered table', () => {
  let $compile;
  let $interval;
  let $q;
  let $rootScope;


  beforeEach(module('/static/angular-components/core/paged-filtered-table-top.html'));
  beforeEach(module('/static/angular-components/core/paged-filtered-table-bottom.html'));
  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    $interval = $injector.get('$interval');
  }));

  const render = (items, withAutoRefresh) => {
    $rootScope.testItems = items;
    if (withAutoRefresh) {
      $rootScope.autoRefreshInterval = 1000;
    }

    // We render the paged filtered table with grr-memory-items-provider.
    // While it means that this unit test actually depends on the working
    // code of grr-memory-items-provider (which is tested separately),
    // this seems to be the easiest/most reasonable way to test that
    // grr-paged-filtered-table is working correctly. Mocking out
    // items providers would require writing code that's almost
    // equal to grr-memory-items-provider code.
    const template = '<div>' +
        '<table>' +
        '<tbody>' +
        '<tr grr-paged-filtered-table grr-memory-items-provider ' +
        'items="testItems" page-size="5" ' +
        'auto-refresh-interval="autoRefreshInterval">' +
        '<td>{$ item.timestamp $}</td>' +
        '<td>{$ item.message $}</td>' +
        '</tr>' +
        '</tbody' +
        '</table>' +
        '</div>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('throws if items provider is not specified', () => {
    // We need outer container, as grr-paged-filtered-table inserts directives
    // before and after containing table.
    const template = '<div><table><tbody><tr grr-paged-filtered-table />' +
        '</tbody></table></div>';
    const compiledTemplate = $compile(template);
    expect(() => {
      compiledTemplate($rootScope);
    }).toThrow(Error('Data provider not specified.'));
  });

  it('shows empty table when there are no elements', () => {
    const element = render([]);

    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(0);
  });

  it('shows 2 rows for 2 items', () => {
    const element = render(
        [{timestamp: 42, message: 'foo'}, {timestamp: 43, message: 'bar'}]);

    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(2);
    expect(element.text()).toContain('2 entries');

    expect($('table tr:eq(0) td:eq(0):contains(42)', element).length).
        toBe(1);
    expect($('table tr:eq(0) td:eq(1):contains(foo)', element).length).
        toBe(1);
    expect($('table tr:eq(1) td:eq(0):contains(43)', element).length).
        toBe(1);
    expect($('table tr:eq(1) td:eq(1):contains(bar)', element).length).
        toBe(1);
  });


  const checkItemsAreShown = (itemsToCheck, element) => {
    angular.forEach(itemsToCheck, (item) => {
      const foundElems = $('td:contains(' + item.message + ')', element);
      expect(foundElems.length).toBe(1);
    });
  };

  const checkItemsAreNotShown = (itemsToCheck, element) => {
    angular.forEach(itemsToCheck, (item) => {
      const foundElems = $('td:contains(' + item.message + ')', element);
      expect(foundElems.length).toBe(0);
    });
  };

  it('switches between pages correctly when there are 2 pages', () => {
    const items = [];
    for (let i = 0; i < 10; ++i) {
      items.push({timestamp: i,
        message: 'message_' + i.toString()});
    }

    const element = render(items);

    checkItemsAreShown(items.slice(0, 5), element);
    checkItemsAreNotShown(items.slice(5), element);

    browserTriggerEvent($('a:contains(Next)', element), 'click');
    checkItemsAreNotShown(items.slice(0, 5), element);
    checkItemsAreShown(items.slice(5), element);

    browserTriggerEvent($('a:contains(Previous)', element), 'click');
    checkItemsAreShown(items.slice(0, 5), element);
    checkItemsAreNotShown(items.slice(5), element);
  });

  it('switches between pages correctly when there are 15 pages', () => {
    const items = [];
    for (let i = 0; i < 5 * 15; ++i) {
      items.push({timestamp: i,
        message: 'message_' + i.toString()});
    }

    const element = render(items);

    for (let i = 0; i < 15; ++i) {
      const pageLink = $('a', element).filter(function() {
        return $(this).text() == (i + 1).toString();
      });
      browserTriggerEvent(pageLink, 'click');

      checkItemsAreShown(items.slice(i * 5, i * 5 + 5), element);
      if (i > 0) {
        checkItemsAreNotShown(items.slice((i - 1) * 5, i * 5), element);
      }
      if (i < 14) {
        checkItemsAreNotShown(items.slice((i + 1) * 5, items.length), element);
      }
    }
  });

  it('filters collection of 5 elements correctly', () => {
    const someItems = [
      {message: 'some1'},
      {message: 'some2'},
    ];
    const otherItems = [
      {message: 'other1'},
      {message: 'other2'},
      {message: 'other3'},
    ];

    const element = render(someItems.concat(otherItems));
    checkItemsAreShown(someItems, element);
    checkItemsAreShown(otherItems, element);

    $('input.search-query', element).val('some');
    browserTriggerEvent($('input.search-query', element), 'input');
    browserTriggerEvent($('button:contains(Filter)', element), 'click');

    expect(element.text()).toContain('Filtered by: some');
    checkItemsAreShown(someItems, element);
    checkItemsAreNotShown(otherItems, element);

    $('input.search-query', element).val('');
    browserTriggerEvent($('input.search-query', element), 'input');
    browserTriggerEvent($('button:contains(Filter)', element), 'click');

    expect(element.text()).not.toContain('Filtered by');
    checkItemsAreShown(someItems, element);
    checkItemsAreShown(otherItems, element);
  });

  it('loads more filtered results when "Fetch More" is clicked', () => {
    const someItems = [
      {message: 'some1'},
      {message: 'some2'},
      {message: 'some3'},
      {message: 'some4'},
      {message: 'some5'},
      {message: 'some6'},
      {message: 'some7'},
    ];
    const otherItems = [
      {message: 'other1'},
      {message: 'other2'},
      {message: 'other3'},
    ];

    const element = render(someItems.concat(otherItems));

    $('input.search-query', element).val('some');
    browserTriggerEvent($('input.search-query', element), 'input');
    browserTriggerEvent($('button:contains(Filter)', element), 'click');

    checkItemsAreShown(someItems.slice(0, 5), element);
    checkItemsAreNotShown(someItems.slice(5), element);
    checkItemsAreNotShown(otherItems, element);

    browserTriggerEvent($('button:contains("Fetch More")', element), 'click');
    checkItemsAreShown(someItems, element);
    checkItemsAreNotShown(otherItems, element);
  });

  it('fetches 5 pages of filtered results when "Fetch 5" is clicked', () => {
    const someItems = [];
    for (let i = 0; i < 35; ++i) {
      someItems.push({message: 'some_' + i.toString(36)});
    }

    const otherItems = [];
    for (let i = 0; i < 20; ++i) {
      otherItems.push({message: 'other' + i.toString(36)});
    }

    const element = render(someItems.concat(otherItems));

    $('input.search-query', element).val('some');
    browserTriggerEvent($('input.search-query', element), 'input');
    browserTriggerEvent($('button:contains(Filter)', element), 'click');

    browserTriggerEvent($('a:contains("Fetch 25")', element), 'click');
    // 5 items were shown initially, we fetched 25 more, so 30 should be
    // shown.
    checkItemsAreShown(someItems.slice(0, 30), element);
    // 5 items (30..35) were left unshown.
    checkItemsAreNotShown(someItems.slice(30, 35), element);
    // Elements that do not match the filter shouldn't be shown at all.
    checkItemsAreNotShown(otherItems, element);
  });

  describe('with auto-refresh-interval set', () => {
    it('adds new element to the end of the list', () => {
      const someItems = [
        {message: 'some1'},
        {message: 'some2'},
      ];

      const element = render(someItems, true);
      checkItemsAreShown(someItems, element);

      someItems.push({message: 'some3'});
      $interval.flush(1000);
      checkItemsAreShown(someItems, element);
    });

    it('updates total count', () => {
      const someItems = [
        {message: 'some1'},
        {message: 'some2'},
      ];

      const element = render(someItems, true);
      expect(element.text().indexOf('2 entries') != -1 ).toBe(true);

      for (let i = 0; i < 5; ++i) {
        someItems.push({message: 'somethingelse'});
      }
      $interval.flush(1000);
      expect(element.text().indexOf('7 entries') != -1 ).toBe(true);
    });

    it('updates paging', () => {
      const someItems = [
        {message: 'some1'},
        {message: 'some2'},
      ];

      const element = render(someItems, true);
      expect(element.find('ul.pagination li:contains("2")').length).toBe(0);

      for (let i = 0; i < 5; ++i) {
        someItems.push({message: 'somethingelse'});
      }
      $interval.flush(1000);
      expect(element.find('ul.pagination li:contains("2")').length).toBe(1);
    });

    it('does not auto-update in filtered mode', () => {
      const someItems = [
        {message: 'some1'},
        {message: 'some2'},
      ];

      const element = render(someItems, true);
      $('input.search-query', element).val('some');
      browserTriggerEvent($('input.search-query', element), 'input');
      browserTriggerEvent($('button:contains(Filter)', element), 'click');

      checkItemsAreShown(someItems, element);

      someItems.push({message: 'some3'});
      $interval.flush(1000);
      checkItemsAreShown(someItems.slice(0, 2), element);
      checkItemsAreNotShown(someItems.slice(2, 3), element);
    });

    it('does not auto-update if full page is shown', () => {
      // Page size is 5.
      const someItems = [
        {message: 'some1'},
        {message: 'some2'},
        {message: 'some3'},
        {message: 'some4'},
        {message: 'some5'},
      ];

      const element = render(someItems, true);
      checkItemsAreShown(someItems, element);

      someItems[0] = {message: 'someother'};
      someItems.push({message: 'some6'});
      $interval.flush(1000);
      checkItemsAreShown(someItems.slice(1, 5), element);
      checkItemsAreNotShown(someItems.slice(0, 1), element);
      checkItemsAreNotShown(someItems.slice(5, 6), element);
    });

    it('skips results of the obsolete request if page is changed', () => {
      // Page size is 5.
      const someItems = [
        {message: 'some1'},
        {message: 'some2'},
        {message: 'some3'},
        {message: 'some4'},
        {message: 'some5'},
        {message: 'some6'},
      ];

      const element = render(someItems, true);
      browserTriggerEvent($('a:contains(Next)', element), 'click');
      checkItemsAreShown(someItems.slice(5), element);

      const deferred1 = $q.defer();
      const deferred2 = $q.defer();
      spyOn(MemoryItemsProviderController.prototype, 'fetchItems')
          .and.returnValue(deferred1.promise)
          .and.returnValue(deferred2.promise);

      // First let the auto-update trigger.
      $interval.flush(1000);

      // Second let's go back to the previous page.
      browserTriggerEvent($('a:contains(Previous)', element), 'click');

      // Resolve the non-auto-update deferred.
      deferred2.resolve({items: someItems.slice(0, 5)});
      $rootScope.$apply();
      checkItemsAreShown(someItems.slice(0, 5), element);

      // Resolve the now-obsolete deferred corresponding to the auto-update
      // action. Nothing should happen.
      deferred1.resolve({items: someItems.slice(5, 6)});
      $rootScope.$apply();
      checkItemsAreShown(someItems.slice(0, 5), element);
      checkItemsAreNotShown(someItems.slice(5, 6), element);
    });

    it('does not start auto-update request if one is in progress', () => {
      // Page size is 5.
      const someItems = [
        {message: 'some1'},
      ];

      render(someItems, true);

      const deferred = $q.defer();
      spyOn(MemoryItemsProviderController.prototype, 'fetchItems')
          .and.returnValue(deferred.promise);

      // Let the auto-update trigger.
      $interval.flush(1000);

      // And once again.
      $interval.flush(1000);

      // Check that fetchItems() was called just once.
      expect(MemoryItemsProviderController.prototype.fetchItems)
          .toHaveBeenCalledTimes(1);
    });
  });
});


exports = {};
