'use strict';

goog.module('grrUi.core.pagedFilteredTableDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive for displaying the top pane of the paged/filtered table.
 *
 * @return {!angular.Directive}
 * @ngInject
 * @export
 */
exports.TableTopDirective = function() {
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
exports.TableTopDirective.directive_name = 'grrPagedFilteredTableTop';



/**
 * Directive for displaying the bottom part of the paged/filtered table.
 *
 * @return {!angular.Directive}
 * @ngInject
 * @export
 */
exports.TableBottomDirective = function() {
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
exports.TableBottomDirective.directive_name = 'grrPagedFilteredTableBottom';



/**
 * Controller for PagedFilteredTableDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {function(function(angular.jQuery, angular.Scope), angular.jQuery)}
 *     $transclude
 * @param {!angular.$compile} $compile
 * @param {!angular.$interval} $interval
 * @ngInject
 */
const PagedFilteredTableController = function(
    $scope, $element, $transclude, $compile, $interval) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?number} */
  this.scope_.pageSize;

  /** @type {?number} */
  this.scope_.autoRefreshInterval;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /**
   * @private {function(function(angular.jQuery, angular.Scope),
   *     angular.jQuery)}
   */
  this.transclude_ = $transclude;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  // Internal state.

  /**
   * Items provider to be used for fetching items to be displayed.
   * @export {grrUi.core.itemsProviderController.ItemsProviderController}
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
   * @export {?number}
   */
  this.totalCount;

  /**
   * Number of elements shown on a single page.
   * @export {number}
   */
  this.pageSize = this.scope_.pageSize ||
      PagedFilteredTableController.DEFAULT_PAGE_SIZE;

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

  /**
   * Request counter used to ignore obsolete requests (request becomes obsolete
   * if another request gets sent as a result of a user action).
   * @private {number}
   */
  this.requestCounter_ = 0;

  /**
   * True, if there's an auto-refresh request currently in progress.
   * @private {boolean}
   */
  this.autoRefreshInProgress_ = false;

  this.addTopDirective_();
  this.addBottomDirective_();

  this.scope_.$watch('::controller.itemsProvider', function() {
    this.fetchUnfilteredItems(true);
  }.bind(this));

  if (this.scope_.autoRefreshInterval) {
    // Initialize the timer used to refresh data in the table.
    /** @type {!angular.$q.Promise} */
    var refreshTimer = this.interval_(
        this.onAutoRefresh_.bind(this),
        this.scope_.autoRefreshInterval);

    // Destroy the timer when the shared directive's scope is destroyed.
    this.scope_.$on('$destroy', function() {
      this.interval_.cancel(refreshTimer);
    }.bind(this));
  }
};



/** @const */
PagedFilteredTableController.DEFAULT_PAGE_SIZE = 50;


/**
 * Adds grr-paged-filtered-table-top directive before the table.
 *
 * @private
 */
PagedFilteredTableController.prototype.addTopDirective_ = function() {
  var template = /** @type {angular.jQuery} */ (angular.element(
      '<grr-paged-filtered-table-top parent-controller="controller" />'));
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
  var template = /** @type {angular.jQuery} */ (angular.element(
      '<grr-paged-filtered-table-bottom parent-controller="controller" />'));
  var table = this.element_.closest('table');
  template.insertAfter(table);
  this.compile_(template)(this.scope_);
};


/**
 * Wraps a given function with a check that ensures that it won't get executed
 * if the request counter changes between this call and the time when the
 * callback gets triggered.
 *
 * @param {Function} callback Promise callback to receive data.
 * @return {Function} Wrapped callback.
 * @private
 */
PagedFilteredTableController.prototype.wrapWithCounterCheck_ = function(
    callback) {
  this.requestCounter_ += 1;
  var curRequestCounter = this.requestCounter_;

  return function(data) {
    if (this.requestCounter_ == curRequestCounter) {
      return callback(data);
    }
  }.bind(this);
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
  this.setItems_([]);

  this.itemsProvider.fetchItems(
      this.currentPage * this.pageSize, this.pageSize, withTotalCount).then(
          this.wrapWithCounterCheck_(
              this.onFetchedUnfilteredItems_.bind(this)));
};


/**
 * Handles fetched unfiltered items.
 *
 * @param {!grrUi.core.itemsProviderController.Items} items
 * @private
 */
PagedFilteredTableController.prototype.onFetchedUnfilteredItems_ = function(
    items) {
  this.showLoading = false;
  this.setItems_(items.items);

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
  this.filterApplied = (this.filterValue != '');
  this.filterFinished = false;
  this.currentPage = 0;
  this.paginationSelectedPage = 1;
  this.setItems_([]);

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
          this.wrapWithCounterCheck_(this.onFetchedFilteredItems_.bind(this)));
};


/**
 * Handles fetched filtered items.
 *
 * @param {!grrUi.core.itemsProviderController.Items} items
 * @private
 */
PagedFilteredTableController.prototype.onFetchedFilteredItems_ = function(
    items) {
  this.showLoading = false;
  this.setItems_(this.items.concat(items.items));

  if (items.items.length == 0 || items.items.length % this.pageSize != 0) {
    this.filterFinished = true;
  }
};


/**
 * Changes the items list, updating the presentation accordingly.
 *
 * @param {!Array<Object>} newItems
 * @private
 */
PagedFilteredTableController.prototype.setItems_ = function(newItems) {
  var indexOffset = 0;
  if (angular.equals(this.items, newItems.slice(0, this.items.length))) {
    indexOffset = this.items.length;
  } else {
    this.element_.siblings().remove();
  }

  this.items = newItems;

  for (var i = indexOffset; i < this.items.length; ++i) {
    this.transclude_(function(clone, scope) {
      scope.item = this.items[i];
      scope.$index = i;
      this.element_.parent().append(clone);
    }.bind(this), this.element_.parent());
  }
};

/**
 * Triggered periodically if autoRefreshInterval binding is set.
 *
 * @private
 */
PagedFilteredTableController.prototype.onAutoRefresh_ = function() {
  if (this.filterApplied || this.items.length >= this.pageSize ||
      this.autoRefreshInProgress_) {
    return;
  }

  var callback = this.wrapWithCounterCheck_(
      this.onFetchedUnfilteredItems_.bind(this));

  this.autoRefreshInProgress_ = true;
  this.itemsProvider.fetchItems(
      this.currentPage * this.pageSize,
      this.pageSize, true).then(callback).finally(function() {
        this.autoRefreshInProgress_ = false;
      }.bind(this));
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
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.PagedFilteredTableDirective = function() {
  return {
    scope: {
      pageSize: '=?',
      autoRefreshInterval: '=?'
    },
    transclude: 'element',
    restrict: 'A',
    priority: 1000,
    terminal: true,
    require: ['?grrMemoryItemsProvider',
              '?grrApiItemsProvider'],
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
exports.PagedFilteredTableDirective.directive_name = 'grrPagedFilteredTable';
