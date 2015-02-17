'use strict';

goog.provide('grrUi.core.pagedFilteredTableDirective.PagedFilteredTableController');
goog.provide('grrUi.core.pagedFilteredTableDirective.PagedFilteredTableDirective');
goog.provide('grrUi.core.pagedFilteredTableDirective.TableBottomDirective');
goog.provide('grrUi.core.pagedFilteredTableDirective.TableTopDirective');


goog.scope(function() {



/**
 * Directive for displaying the top pane of the paged/filtered table.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.pagedFilteredTableDirective.TableTopDirective = function() {
  return {
    scope: {
      parentController: '='
    },
    require: '^grrPagedFilteredTable',
    templateUrl: '/static/angular-components/core/' +
        'paged-filtered-table-top.html',
    restrict: 'E'
  };
};


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
grrUi.core.pagedFilteredTableDirective.TableTopDirective.
    directive_name = 'grrPagedFilteredTableTop';



/**
 * Directive for displaying the bottom part of the paged/filtered table.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.pagedFilteredTableDirective.TableBottomDirective = function() {
  return {
    scope: {
      parentController: '='
    },
    require: '^grrPagedFilteredTable',
    templateUrl: '/static/angular-components/core/' +
        'paged-filtered-table-bottom.html',
    restrict: 'E'
  };
};


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
grrUi.core.pagedFilteredTableDirective.TableBottomDirective.
    directive_name = 'grrPagedFilteredTableBottom';



/**
 * Controller for PagedFilteredTableDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.JQLite} $element
 * @param {function(function(angular.JQLite, angular.Scope), angular.JQLite)}
 *     $transclude
 * @param {!angular.$compile} $compile
 * @ngInject
 */
grrUi.core.pagedFilteredTableDirective.PagedFilteredTableController = function(
    $scope, $element, $transclude, $compile) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {number} */
  this.scope_.pageSize;

  /** @private {!angular.JQLite} */
  this.element_ = $element;

  /** @private {function(function(angular.JQLite, angular.Scope),
      angular.JQLite)} */
  this.transclude_ = $transclude;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  // Internal state.

  /**
   * Items provider to be used for fetching items to be displayed.
   * @export {!grrUi.core.itemsProviderController.ItemsProviderController}
   */
  this.itemsProvider;

  /**
   * Currently shown page.
   * @export {number}
   */
  this.currentPage = 0;

  /**
   * Page currently selected by the pagination UI control. This is a pure UI
   * binding and has no connection with currentPage. Pagination control is
   * reset by assigning 1 to this variable.
   * @export {number}
   */
  this.paginationSelectedPage = 1;

  /**
   * If true, "Loading..." message should be shown.
   * @export {boolean}
   */
  this.showLoading = true;

  /**
   * Items currently shown.
   * @export {!Array<Object>}
   */
  this.items = [];

  /**
   * Total count of all items - not only the ones that are shown, but the
   * ones on the server.
   * @export {number}
   */
  this.totalCount;

  /**
   * Number of elements shown on a single page.
   * @export {number}
   */
  this.pageSize = this.scope_.pageSize || this.DEFAULT_PAGE_SIZE;

  /**
   * Used for UI binding with a filter edit field.
   * @export {string}
   */
  this.filterEditedValue = '';

  /**
   * Currently used filter value.
   * @export {string}
   */
  this.filterValue = '';

  /**
   * If true, filter is currently applied.
   * @export {boolean}
   */
  this.filterApplied = false;

  /**
   * If true, all the filtered items were fetched, there are no more left.
   * @export {boolean}
   */
  this.filterFinished = false;

  this.addTopDirective_();
  this.addBottomDirective_();

  this.scope_.$watchCollection('controller.items',
                               this.onItemsChange_.bind(this));

  this.scope_.$watch('::controller.itemsProvider', function() {
    this.fetchUnfilteredItems(true);
  }.bind(this));
};

var PagedFilteredTableController =
    grrUi.core.pagedFilteredTableDirective.PagedFilteredTableController;


/** @const */
PagedFilteredTableController.prototype.DEFAULT_PAGE_SIZE = 50;


/**
 * Adds grr-paged-filtered-table-top directive before the table.
 *
 * @private
 */
PagedFilteredTableController.prototype.addTopDirective_ = function() {
  var template = angular.element(
      '<grr-paged-filtered-table-top parent-controller="controller" />');
  var table = this.element_.closest('table');
  template.insertBefore(table);
  this.compile_(template)(this.scope_);
};


/**
 * Adds grr-paged-filtered-table-bottom directive after the table.
 *
 * @private
 */
PagedFilteredTableController.prototype.addBottomDirective_ = function() {
  var template = angular.element(
      '<grr-paged-filtered-table-bottom parent-controller="controller" />');
  var table = this.element_.closest('table');
  template.insertAfter(table);
  this.compile_(template)(this.scope_);
};


/**
 * Fetches unfiltered items for the current page.
 *
 * @param {boolean} withTotalCount If true, fetch total number of items on the
 *     server as well.
 * @export
 */
PagedFilteredTableController.prototype.fetchUnfilteredItems = function(
    withTotalCount) {
  this.showLoading = true;
  this.items = [];

  this.itemsProvider.fetchItems(
      this.currentPage * this.pageSize, this.pageSize, withTotalCount).then(
      this.onFetchedUnfilteredItems_.bind(this));
};


/**
 * Handles fetched unfiltered items.
 *
 * @param {!Array<Object>} items
 * @private
 */
PagedFilteredTableController.prototype.onFetchedUnfilteredItems_ = function(
    items) {
  this.showLoading = false;
  this.items = items;

  if (angular.isDefined(items.totalCount)) {
    this.totalCount = items.totalCount;
  }
};


/**
 * Applies currently typed in filter. If nothing is typed, fetches unfiltered
 * items, otherwise fetches filtered ones.
 *
 * @export
 */
PagedFilteredTableController.prototype.applyFilter = function() {
  this.filterValue = this.filterEditedValue;
  this.filterApplied = (this.filterValue !== '');
  this.filterFinished = false;
  this.currentPage = 0;
  this.paginationSelectedPage = 1;
  this.items = [];

  if (this.filterApplied) {
    this.fetchFilteredItems();
  } else {
    this.fetchUnfilteredItems(false);
  }
};


/**
 * Fetches specified number of pages of filtered items.
 *
 * @param {number=} opt_numPages How many pages of items to fetch.
 * @export
 */
PagedFilteredTableController.prototype.fetchFilteredItems = function(
    opt_numPages) {
  if (angular.isUndefined(opt_numPages)) {
    opt_numPages = 1;
  }
  this.showLoading = true;

  this.itemsProvider.fetchFilteredItems(
      this.filterValue, this.items.length, this.pageSize * opt_numPages).then(
      this.onFetchedFilteredItems_.bind(this));
};


/**
 * Handles fetched filtered items.
 *
 * @param {!Array<Object>} items
 * @private
 */
PagedFilteredTableController.prototype.onFetchedFilteredItems_ = function(
    items) {
  this.showLoading = false;
  this.items = this.items.concat(items);
  if (items.length % this.pageSize !== 0) {
    this.filterFinished = true;
  }
  this.currentPage += Math.ceil(items.length / this.pageSize);
};


/**
 * Handles changes in the items list, updating the presentation accordingly.
 *
 * @param {Array<Object>} newItems
 * @param {Array<Object>} oldItems
 * @private
 */
PagedFilteredTableController.prototype.onItemsChange_ = function(
    newItems, oldItems) {

  var itemsToRender;
  if (this.filterApplied) {
    if (oldItems != newItems.slice(0, oldItems.length)) {
      this.element_.siblings().remove();
      itemsToRender = newItems;
    } else {
      itemsToRender = newItems.slice(oldItems.length, newItems.length);
    }
  } else {
    itemsToRender = newItems;
    this.element_.siblings().remove();
  }

  for (var i = 0; i < itemsToRender.length; ++i) {
    var self = this;
    this.transclude_(function(clone, scope) {
      scope.item = self.items[i];
      scope.$index = i;
      self.element_.parent().append(clone);
    }, this.element_.parent());
  }
};


/**
 * Handles changes in the UI page number binding.
 *
 * @param {number} newPage
 * @export
 */
PagedFilteredTableController.prototype.onPageChange = function(newPage) {
  this.currentPage = newPage;

  if (!this.filterApplied) {
    this.fetchUnfilteredItems(false);
  }
};



/**
 * Directive for displaying paged tables with filtering capability.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.pagedFilteredTableDirective.PagedFilteredTableDirective =
    function() {
  return {
    scope: {
      pageSize: '=?'
    },
    transclude: 'element',
    restrict: 'A',
    priority: 1000,
    terminal: true,
    require: ['?grrMemoryItemsProvider',
              '?grrApiItemsProvider',
              '?grrAff4ItemsProvider'],
    controller: PagedFilteredTableController,
    controllerAs: 'controller',
    link: function(scope, element, attrs, controllers) {
      var providerController = undefined;
      for (var i = 0; i < controllers.length; ++i) {
        if (angular.isObject(controllers[i])) {
          if (angular.isDefined(providerController)) {
            throw new Error('Can have only 1 provider.');
          }
          providerController = controllers[i];
        }
      }
      if (angular.isUndefined(providerController)) {
        throw new Error('Data provider not specified.');
      }

      scope.controller.itemsProvider = providerController;
    }
  };
};


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
grrUi.core.pagedFilteredTableDirective.PagedFilteredTableDirective.
    directive_name = 'grrPagedFilteredTable';


});  // goog.scope
