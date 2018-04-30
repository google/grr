'use strict';

goog.module('grrUi.core.infiniteTableDirectiveTest');

const {InfiniteTableController} = goog.require('grrUi.core.infiniteTableDirective');
const {MemoryItemsProviderController} = goog.require('grrUi.core.memoryItemsProviderDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('infinite table', () => {
  let $compile;
  let $interval;
  let $q;
  let $rootScope;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
    $q = $injector.get('$q');
  }));

  afterEach(() => {
    // We have to clean document's body to remove tables we add there.
    $(document.body).html('');
  });

  const render = (items, noDomAppend, filterValue, withAutoRefresh) => {
    $rootScope.testItems = items;
    if (filterValue) {
      $rootScope.filterValue = filterValue;
    }

    // We render the infinite table with grr-memory-items-provider.
    // While it means that this unit test actually depends on the working
    // code of grr-memory-items-provider (which is tested separately),
    // this seems to be the easiest/most reasonable way to test that
    // grr-infinite-table is working correctly. Mocking out
    // items providers would require writing code that's almost
    // equal to grr-memory-items-provider code.
    const template = '<div>' +
        '<table>' +
        '<tbody>' +
        '<tr grr-infinite-table grr-memory-items-provider ' +
        '    items="testItems" page-size="5"' +
        (withAutoRefresh ? '    auto-refresh-interval="1" ' : '') +
        '    filter-value="filterValue"' +
        '    trigger-update="triggerUpdate">' +
        '  <td>{$ ::item.timestamp $}</td>' +
        '  <td>{$ ::item.message $}</td>' +
        '</tr>' +
        '</tbody' +
        '</table>' +
        '</div>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    if (!noDomAppend) {
      $('body').append(element);
      $interval.flush(1000);
    }

    return element;
  };

  it('throws if items provider is not specified', () => {
    const template = '<table><tbody><tr grr-infinite-table />' +
        '</tbody></table>';
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

    expect($('table tr:eq(0) td:eq(0):contains(42)', element).length).
        toBe(1);
    expect($('table tr:eq(0) td:eq(1):contains(foo)', element).length).
        toBe(1);
    expect($('table tr:eq(1) td:eq(0):contains(43)', element).length).
        toBe(1);
    expect($('table tr:eq(1) td:eq(1):contains(bar)', element).length).
        toBe(1);
  });

  it('does nothing when "Loading..." row is not seen', () => {
    const element = render(
        [{timestamp: 42, message: 'foo'}, {timestamp: 43, message: 'bar'}],
        true);

    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(1);
    expect($('table tr:contains("Loading...")', element).length).toBe(1);

    $interval.flush(1000);
    expect($('table tr', element).length).toBe(1);
    expect($('table tr:contains("Loading...")', element).length).toBe(1);

    $('body').append(element);
    $interval.flush(1000);

    expect($('table tr', element).length).toBe(2);
    expect($('table tr:contains("Loading...")', element).length).toBe(0);
    expect($('table tr:eq(0) td:eq(0):contains(42)', element).length).
        toBe(1);
    expect($('table tr:eq(0) td:eq(1):contains(foo)', element).length).
        toBe(1);
    expect($('table tr:eq(1) td:eq(0):contains(43)', element).length).
        toBe(1);
    expect($('table tr:eq(1) td:eq(1):contains(bar)', element).length).
        toBe(1);
  });

  it('applies the filter when a filter value is set', () => {
    const element = render(
        [{timestamp: 42, message: 'foo'}, {timestamp: 43, message: 'bar'}],
        false, 'foo');

    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(1);

    expect($('table tr:eq(0) td:eq(0):contains(42)', element).length).
        toBe(1);
    expect($('table tr:eq(0) td:eq(1):contains(foo)', element).length).
        toBe(1);
  });

  it('shows an empty table when the filter removes all items', () => {
    const element = render(
        [{timestamp: 42, message: 'foo'}, {timestamp: 43, message: 'bar'}],
        false, 'xxx');

    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(0);
  });

  it('cancels an in-flight request when trigger-update is called', () => {
    const deferred1 = $q.defer();
    const deferred2 = $q.defer();
    spyOn(MemoryItemsProviderController.prototype, 'fetchItems').and
        .returnValues(deferred1.promise, deferred2.promise);

    const element = render([]);
    // Only the 'Loading...' row should be displayed.
    expect($('table tr', element).length).toBe(1);

    // This should trigger yet another call.
    $rootScope.triggerUpdate();
    // Run the timer forward, so that newly displayed 'Loading...' element
    // can be detected.
    $interval.flush(1000);

    deferred2.resolve({
      offset: 0,
      items: [
        {timestamp: 44, message: 'foo2'},
        {timestamp: 45, message: 'bar2'},
      ],
    });
    $rootScope.$apply();

    deferred1.resolve({
      offset: 0,
      items: [
        {timestamp: 42, message: 'foo1'},
        {timestamp: 43, message: 'bar1'},
      ],
    });
    $rootScope.$apply();

    // Check that deferred1's result gets discarded as it
    // returns after the triggerUpdate is called.
    expect($('td:contains("foo2")', element).length).toBe(1);
    expect($('td:contains("bar2")', element).length).toBe(1);
    expect($('td:contains("bar1")', element).length).toBe(0);
    expect($('td:contains("bar1")', element).length).toBe(0);
  });

  describe('with auto refresh turned on', () => {
    const TABLE_KEY = InfiniteTableController.UNIQUE_KEY_NAME;
    const ROW_HASH = InfiniteTableController.ROW_HASH_NAME;

    const transformItems = ((items) => {
      for (let i = 0; i < items.length; ++i) {
        const item = items[i];
        item[TABLE_KEY] = item['message'];
        item[ROW_HASH] = item['timestamp'];
      }
      return items;
    });

    it('adds new element to the beginning of the list', () => {
      const element = render(
          transformItems([
            {timestamp: 42, message: 'foo'}, {timestamp: 43, message: 'bar'}
          ]),
          undefined, undefined, true);

      expect($('table', element).length).toBe(1);
      expect($('table tr', element).length).toBe(2);

      // Update the memory items provider elements and push the clock.
      $rootScope.testItems.push(
          transformItems([{timestamp: 44, message: 'blah'}])[0]);
      $interval.flush(1000);
      expect($('table tr', element).length).toBe(3);

      // New element should be inserted in the beginning of the table.
      expect($('table tr:eq(0) td:eq(0):contains(44)', element).length).
        toBe(1);
      expect($('table tr:eq(0) td:eq(1):contains(blah)', element).length).
          toBe(1);

      // Check that the behavior is stable, i.e. element is added only once.
      $interval.flush(2000);
      expect($('table tr', element).length).toBe(3);
      expect($('table tr:eq(0) td:eq(0):contains(44)', element).length).
        toBe(1);
      expect($('table tr:eq(0) td:eq(1):contains(blah)', element).length).
          toBe(1);

      expect($('table tr:eq(1) td:eq(0):contains(42)', element).length).
        toBe(1);
      expect($('table tr:eq(1) td:eq(1):contains(foo)', element).length).
          toBe(1);

      expect($('table tr:eq(2) td:eq(0):contains(43)', element).length).
        toBe(1);
      expect($('table tr:eq(2) td:eq(1):contains(bar)', element).length).
          toBe(1);
    });

    it('adds multiple new elements in the right order', () => {
      const element = render([], undefined, undefined, true);

      expect($('table tr', element).length).toBe(0);

      // Update the memory items provider elements and push the clock.
      Array.prototype.push.apply(
          $rootScope.testItems,
          transformItems([{timestamp: 42, message: 'foo'},
                          {timestamp: 43, message: 'bar'}]));
      $interval.flush(1000);
      expect($('table tr', element).length).toBe(2);

      // New element should be inserted in the beginning of the table.
      expect($('table tr:eq(0) td:eq(1):contains(foo)', element).length).
        toBe(1);
      expect($('table tr:eq(1) td:eq(1):contains(bar)', element).length).
          toBe(1);
    });

    it('does nothing with the row if row hash has not changed', () => {
      const element = render(
          transformItems([
            {timestamp: 42, message: 'foo'}, {timestamp: 43, message: 'bar'}
          ]),
          undefined, undefined, true);

      expect($('table tr:eq(0) td:eq(0):contains(42)', element).length).
        toBe(1);

      // Change the message, but don't touch the hash.
      $rootScope.testItems[0]["timestamp"] = 88;
      $interval.flush(2000);

      // Result shouldn't be updated, since the hash hasn't changed.
      //
      // (Note that one-time-bindings are used in the template, meaning
      // that each row can only be updated by grr-infinite-table and not
      // via standard Angular bindings mechanism).
      expect($('table tr:eq(0) td:eq(0):contains(42)', element).length).
          toBe(1);
    });

    it('updates the row if row hash has changed', () => {
      const element = render(
          transformItems([
            {timestamp: 42, message: 'foo'}, {timestamp: 43, message: 'bar'}
          ]),
          undefined, undefined, true);

      expect($('table tr:eq(0) td:eq(0):contains(42)', element).length).
        toBe(1);

      // Change the message, but don't touch the hash.
      $rootScope.testItems[0]["timestamp"] = 88;
      transformItems($rootScope.testItems);
      $interval.flush(2000);

      // Result should be updated, since the hash has changed.
      //
      // (Note that one-time-bindings are used in the template, meaning
      // that each row can only be updated by grr-infinite-table and not
      // via standard Angular bindings mechanism).
      expect($('table tr:eq(0) td:eq(0):contains(88)', element).length).
          toBe(1);
    });
  });
});


exports = {};
