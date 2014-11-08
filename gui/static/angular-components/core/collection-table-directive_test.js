'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('collection table', function() {
  var $q, $compile, $rootScope, grrAff4Service;

  beforeEach(module('/static/angular-components/core/collection-table.html'));
  beforeEach(module(grrUi.core.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrAff4Service = $injector.get('grrAff4Service');
  }));

  var collectionFromJson = function(jsonData) {
    var element;

    grrAff4Service.get = function(urn, params) {
      expect(urn).toBe('aff4:/tmp/collection');

      return $q(function(resolve, reject) {
        var resolvedJsonData = angular.copy(jsonData);

        if (angular.isDefined(resolvedJsonData.data) &&
            angular.isDefined(resolvedJsonData.data.items)) {

          var filter = params['filter'];
          if (angular.isDefined(filter)) {
            var filteredItems = [];
            angular.forEach(resolvedJsonData.data.items, function(item) {
              if (item.log_message.match(filter)) {
                filteredItems.push(item);
              }
            });
            resolvedJsonData.data.items = filteredItems;
          }

          var offset = params['offset'];
          if (!angular.isDefined(offset)) {
            offset = 0;
          }

          var count = params['count'];
          if (!angular.isDefined(count)) {
            count = 1e6;
          }
          resolvedJsonData.data.items = resolvedJsonData.data.items.slice(
              offset, offset + count);
        }

        resolve(resolvedJsonData);
      });
    };
    var template =
        '<grr-collection-table collection-urn="aff4:/tmp/collection" ' +
        '   page-size="5">' +
        '   <div class="table-cell">{$ item.log_message $}</div>' +
        '</grr-collection-table>';
    element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows empty table when collection is not found', function() {
    var element = collectionFromJson({
      data: {
      }
    });
    expect(element.text()).toContain('No entries');
    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(0);
  });

  it('shows 2 elements when collection has 2 elements', function() {
    var element = collectionFromJson({
      data: {
        items: [
          {log_message: 'foo'},
          {log_message: 'bar'}
        ],
        total_count: 2
      }
    });
    expect(element.text()).toContain('2 entries');
    expect($('table', element).length).toBe(1);
    expect($('table tr', element).length).toBe(2);
    expect($('table tr:eq(0) .table-cell:contains(foo)', element).length).
        toBe(1);
    expect($('table tr:eq(1) .table-cell:contains(bar)', element).length).
        toBe(1);
  });

  var checkItemsAreShown = function(itemsToCheck, element) {
    angular.forEach(itemsToCheck, function(item) {
      var foundElems = $('.table-cell:contains(' + item.log_message + ')',
                         element);
      expect(foundElems.length).toBe(1);
    });
  };

  var checkItemsAreNotShown = function(itemsToCheck, element) {
    angular.forEach(itemsToCheck, function(item) {
      var foundElems = $('.table-cell:contains(' + item.log_message + ')',
                         element);
      expect(foundElems.length).toBe(0);
    });
  };

  it('switches between pages correctly when there are 2 pages', function() {
    var items = [];
    for (var i = 0; i < 10; ++i) {
      items.push({log_message: 'message_' + i.toString()});
    }

    var element = collectionFromJson({
      data: {
        items: items,
        total_count: items.length
      }
    });

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
      items.push({log_message: 'message_' + i.toString()});
    }

    var element = collectionFromJson({
      data: {
        items: items,
        total_count: items.length
      }
    });

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
      {log_message: 'some1'},
      {log_message: 'some2'}
    ];
    var otherItems = [
      {log_message: 'other1'},
      {log_message: 'other2'},
      {log_message: 'other3'}
    ];

    var element = collectionFromJson({
      data: {
        items: someItems.concat(otherItems),
        total_count: someItems.length + otherItems.length
      }
    });

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
      {log_message: 'some1'},
      {log_message: 'some2'},
      {log_message: 'some3'},
      {log_message: 'some4'},
      {log_message: 'some5'},
      {log_message: 'some6'},
      {log_message: 'some7'}
    ];
    var otherItems = [
      {log_message: 'other1'},
      {log_message: 'other2'},
      {log_message: 'other3'}
    ];

    var element = collectionFromJson({
      data: {
        items: someItems.concat(otherItems),
        total_count: someItems.length + otherItems.length
      }
    });

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

  it('fetches all filtered results when "Fetch All" is clicked', function() {
    var someItems = [];
    for (var i = 0; i < 20; ++i) {
      someItems.push({log_message: 'some_' + i.toString(36)});
    }

    var otherItems = [];
    for (i = 0; i < 20; ++i) {
      otherItems.push({log_message: 'other' + i.toString(36)});
    }

    var element = collectionFromJson({
      data: {
        items: someItems.concat(otherItems),
        total_count: someItems.length + otherItems.length
      }
    });

    $('input.search-query', element).val('some');
    browserTrigger($('input.search-query', element), 'input');
    browserTrigger($('button:contains(Filter)', element), 'click');

    browserTrigger($('a:contains("Fetch All")', element), 'click');
    checkItemsAreShown(someItems, element);
    checkItemsAreNotShown(otherItems, element);
  });
});
