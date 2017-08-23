'use strict';

goog.require('grrUi.core.infiniteTableDirective.InfiniteTableController');
goog.require('grrUi.core.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('infinite table', function() {
  var $compile, $rootScope, $interval;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
  }));

  afterEach(function() {
    // We have to clean document's body to remove tables we add there.
    $(document.body).html('');
  });

  var render = function(items, noDomAppend, filterValue, withAutoRefresh) {
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
    var template =
        '<div>' +
        '<table>' +
        '<tbody>' +
        '<tr grr-infinite-table grr-memory-items-provider ' +
        '    items="testItems" page-size="5"' +
        (withAutoRefresh ? '    auto-refresh-interval="1" ' : '') +
        '    filter-value="filterValue">' +
        '  <td>{$ ::item.timestamp $}</td>' +
        '  <td>{$ ::item.message $}</td>' +
        '</tr>' +
        '</tbody' +
        '</table>' +
        '</div>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    if (!noDomAppend) {
      $('body').append(element);
      $interval.flush(1000);
    }

    return element;
  };

  it('throws if items provider is not specified', function() {
    var template = '<table><tbody><tr grr-infinite-table />' +
        '</tbody></table>';
    var compiledTemplate = $compile(template);
    expect(function() { compiledTemplate($rootScope); }).toThrow(
        Error('Data provider not specified.'));
  });

  it('shows empty table when there are no elements', function() {
    var element = render([]);

    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(0);
  });

  it('shows 2 rows for 2 items', function() {
    var element = render([{timestamp: 42, message: 'foo'},
                          {timestamp: 43, message: 'bar'}]);

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

  it('does nothing when "Loading..." row is not seen', function() {
    var element = render([{timestamp: 42, message: 'foo'},
                          {timestamp: 43, message: 'bar'}], true);

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

  it('applies the filter when a filter value is set', function() {
    var element = render([{timestamp: 42, message: 'foo'},
                          {timestamp: 43, message: 'bar'}], false, 'foo');

    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(1);

    expect($('table tr:eq(0) td:eq(0):contains(42)', element).length).
        toBe(1);
    expect($('table tr:eq(0) td:eq(1):contains(foo)', element).length).
        toBe(1);
  });

  it('shows an empty table when the filter removes all items', function() {
    var element = render([{timestamp: 42, message: 'foo'},
                          {timestamp: 43, message: 'bar'}], false, 'xxx');

    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(0);
  });

  describe('with auto refresh turned on', function() {
    var TABLE_KEY =
        grrUi.core.infiniteTableDirective.InfiniteTableController
        .UNIQUE_KEY_NAME;
    var ROW_HASH =
        grrUi.core.infiniteTableDirective.InfiniteTableController
        .ROW_HASH_NAME;

    var transformItems = function(items) {
      for (var i = 0; i < items.length; ++i) {
        var item = items[i];
        item[TABLE_KEY] = item['message'];
        item[ROW_HASH] = item['timestamp'];
      }
      return items;
    };

    it('adds new element to the beginning of the list', function() {
      var element = render(
          transformItems([{timestamp: 42, message: 'foo'},
                          {timestamp: 43, message: 'bar'}]),
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

    it('does nothing with the row if row hash has not changed', function() {
      var element = render(
          transformItems([{timestamp: 42, message: 'foo'},
                          {timestamp: 43, message: 'bar'}]),
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

    it('updates the row if row hash has changed', function() {
      var element = render(
          transformItems([{timestamp: 42, message: 'foo'},
                          {timestamp: 43, message: 'bar'}]),
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
