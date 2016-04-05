'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('paged filtered table', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/core/paged-filtered-table-top.html'));
  beforeEach(module('/static/angular-components/core/paged-filtered-table-bottom.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var render = function(items) {
    $rootScope.testItems = items;

    // We render the paged filtered table with grr-memory-items-provider.
    // While it means that this unit test actually depends on the working
    // code of grr-memory-items-provider (which is tested separately),
    // this seems to be the easiest/most reasonable way to test that
    // grr-paged-filtered-table is working correctly. Mocking out
    // items providers would require writing code that's almost
    // equal to grr-memory-items-provider code.
    var template =
        '<div>' +
        '<table>' +
        '<tbody>' +
        '<tr grr-paged-filtered-table grr-memory-items-provider ' +
        'items="testItems" page-size="5">' +
        '<td>{$ item.timestamp $}</td>' +
        '<td>{$ item.message $}</td>' +
        '</tr>' +
        '</tbody' +
        '</table>' +
        '</div>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('throws if items provider is not specified', function() {
    // We need outer container, as grr-paged-filtered-table inserts directives
    // before and after containing table.
    var template = '<div><table><tbody><tr grr-paged-filtered-table />' +
        '</tbody></table></div>';
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


  var checkItemsAreShown = function(itemsToCheck, element) {
    angular.forEach(itemsToCheck, function(item) {
      var foundElems = $('td:contains(' + item.message + ')',
                         element);
      expect(foundElems.length).toBe(1);
    });
  };

  var checkItemsAreNotShown = function(itemsToCheck, element) {
    angular.forEach(itemsToCheck, function(item) {
      var foundElems = $('td:contains(' + item.message + ')',
                         element);
      expect(foundElems.length).toBe(0);
    });
  };

  it('switches between pages correctly when there are 2 pages', function() {
    var items = [];
    for (var i = 0; i < 10; ++i) {
      items.push({timestamp: i,
        message: 'message_' + i.toString()});
    }

    var element = render(items);

    checkItemsAreShown(items.slice(0, 5), element);
    checkItemsAreNotShown(items.slice(5), element);

    browserTrigger($('a:contains(Next)', element), 'click');
    checkItemsAreNotShown(items.slice(0, 5), element);
    checkItemsAreShown(items.slice(5), element);

    browserTrigger($('a:contains(Previous)', element), 'click');
    checkItemsAreShown(items.slice(0, 5), element);
    checkItemsAreNotShown(items.slice(5), element);
  });

  it('switches between pages correctly when there are 15 pages', function() {
    var items = [];
    for (var i = 0; i < 5 * 15; ++i) {
      items.push({timestamp: i,
        message: 'message_' + i.toString()});
    }

    var element = render(items);

    for (var i = 0; i < 15; ++i) {
      var pageLink = $('a', element).filter(function() {
        return $(this).text() == (i + 1).toString();
      });
      browserTrigger(pageLink, 'click');

      checkItemsAreShown(items.slice(i * 5, i * 5 + 5), element);
      if (i > 0) {
        checkItemsAreNotShown(items.slice((i - 1) * 5, i * 5), element);
      }
      if (i < 14) {
        checkItemsAreNotShown(items.slice((i + 1) * 5, items.length), element);
      }
    }
  });

  it('filters collection of 5 elements correctly', function() {
    var someItems = [
      {message: 'some1'},
      {message: 'some2'}
    ];
    var otherItems = [
      {message: 'other1'},
      {message: 'other2'},
      {message: 'other3'}
    ];

    var element = render(someItems.concat(otherItems));
    checkItemsAreShown(someItems, element);
    checkItemsAreShown(otherItems, element);

    $('input.search-query', element).val('some');
    browserTrigger($('input.search-query', element), 'input');
    browserTrigger($('button:contains(Filter)', element), 'click');

    expect(element.text()).toContain('Filtered by: some');
    checkItemsAreShown(someItems, element);
    checkItemsAreNotShown(otherItems, element);

    $('input.search-query', element).val('');
    browserTrigger($('input.search-query', element), 'input');
    browserTrigger($('button:contains(Filter)', element), 'click');

    expect(element.text()).not.toContain('Filtered by');
    checkItemsAreShown(someItems, element);
    checkItemsAreShown(otherItems, element);
  });

  it('loads more filtered results when "Fetch More" is clicked', function() {
    var someItems = [
      {message: 'some1'},
      {message: 'some2'},
      {message: 'some3'},
      {message: 'some4'},
      {message: 'some5'},
      {message: 'some6'},
      {message: 'some7'}
    ];
    var otherItems = [
      {message: 'other1'},
      {message: 'other2'},
      {message: 'other3'}
    ];

    var element = render(someItems.concat(otherItems));

    $('input.search-query', element).val('some');
    browserTrigger($('input.search-query', element), 'input');
    browserTrigger($('button:contains(Filter)', element), 'click');

    checkItemsAreShown(someItems.slice(0, 5), element);
    checkItemsAreNotShown(someItems.slice(5), element);
    checkItemsAreNotShown(otherItems, element);

    browserTrigger($('button:contains("Fetch More")', element), 'click');
    checkItemsAreShown(someItems, element);
    checkItemsAreNotShown(otherItems, element);
  });

  it('fetches 5 pages of filtered results when "Fetch 5" is clicked',
     function() {
       var someItems = [];
       for (var i = 0; i < 35; ++i) {
         someItems.push({message: 'some_' + i.toString(36)});
       }

       var otherItems = [];
       for (i = 0; i < 20; ++i) {
         otherItems.push({message: 'other' + i.toString(36)});
       }

       var element = render(someItems.concat(otherItems));

       $('input.search-query', element).val('some');
       browserTrigger($('input.search-query', element), 'input');
       browserTrigger($('button:contains(Filter)', element), 'click');

       browserTrigger($('a:contains("Fetch 25")', element), 'click');
       // 5 items were shown initially, we fetched 25 more, so 30 should be
       // shown.
       checkItemsAreShown(someItems.slice(0, 30), element);
       // 5 items (30..35) were left unshown.
       checkItemsAreNotShown(someItems.slice(30, 35), element);
       // Elements that do not match the filter shouldn't be shown at all.
       checkItemsAreNotShown(otherItems, element);
     });
});
