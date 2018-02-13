'use strict';

goog.module('grrUi.core.infiniteTableDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for InfiniteTableDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.Attributes} $attrs
 * @param {!angular.jQuery} $element
 * @param {!angular.$interval} $interval
 * @param {function(function(angular.jQuery, angular.Scope))} $transclude
 * @param {!angular.$parse} $parse
 * @param {!angular.$log} $log
 * @ngInject
 */
exports.InfiniteTableController = function(
    $scope, $attrs, $element, $interval, $transclude, $parse, $log) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.Attributes} */
  this.attrs_ = $attrs;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {function(function(angular.jQuery, angular.Scope))} */
  this.transclude_ = $transclude;

  /** @private {!angular.$log} */
  this.log_ = $log;

  // Internal state.

  /**
   * Items provider to be used for fetching items to be displayed.
   * @export {grrUi.core.itemsProviderController.ItemsProviderController}
   */
  this.itemsProvider;

  /**
   * List of currently fetched items.
   * @private {!Array<Object>}
   */
  this.fetchedItems_ = [];

  /**
   * Current page index. Used when calculating ranges of items to be fetched.
   * @private {number}
   */
  this.currentPage_ = 0;

  /**
   * If this is bigger than currentPage, new pages of data will be fetched
   * until currentPage == showUntilPage (currentPage gets incremented every
   * time a new page is fetched). This mechanism is used when triggerUpdate
   * is called, so that same amount of data is displayed after the update.
   * @private {number}
   */
  this.showUntilPage_ = 0;

  /**
   * Counter that's incremented every time a full update is triggered.
   * This is done so that results of requests that are in-flight when
   * an update is triggered can be safely ignored.
   * @private {number}
   */
  this.updateCounter_ = 0;

  /**
   * @private {string}
   */
  this.filterValue_;

  /**
   * True, if there's a request currently in progress.
   * @private {boolean}
   */
  this.loadingInProgress_ = false;

  /**
   * True, if there's an auto-refresh request currently in progress.
   * @private {boolean}
   */
  this.autoRefreshInProgress_ = false;

  /**
   * Root element where all the rendered data will be appended to.
   * @private {angular.jQuery}
   */
  this.rootElement_ = this.element_.parent();

  /**
   * Page size - if not specified by the user, defaults to 50.
   * @private {number}
   */
  this.pageSize_ = Number($scope.$eval(this.attrs_['pageSize'])) ||
      InfiniteTableController.DEFAULT_PAGE_SIZE;

  /**
   * Dictionary with a list of currently shown elements.
   * Used to make graceful updates (without reloading everything) possible.
   * @private {Object<string, Array<Object>>}
   */
  this.elementScopes_ = {};

  // Replace the directive's element with table-loading row.
  var template = angular.element(InfiniteTableController.LOADING_TEMPLATE);
  this.element_.replaceWith(template);

  // If triggerUpdate attribute is defined, assign own triggerUpdate function
  // to it. This way users of the directive will be able to trigger updates.
  if (angular.isDefined(this.attrs_['triggerUpdate'])) {
    var parsedExpression = $parse(this.attrs_['triggerUpdate']);
    parsedExpression.assign(this.scope_, this.triggerUpdate.bind(this));
  }

  // Initialize timer used to check whether table-loading element is visible.
  /** @type {!angular.$q.Promise} */
  var loadingTimer = this.interval_(this.checkIfTableLoadingIsVisible_.bind(this),
                                    100);

  // Destroy the timer when the shared directive's scope is destroyed.
  this.scope_.$on('$destroy', function() {
    this.interval_.cancel(loadingTimer);
  }.bind(this));

  /**
   * Auto refresh interval in milliseconds. If specified the table will
   * auto-refresh itself periodically, gracefully inserting new elements and
   * updating changed elements.
   * @private {number}
   */
  this.autoRefreshInterval_ = Number(
      $scope.$eval(this.attrs_['autoRefreshInterval']));

  if (this.autoRefreshInterval_) {
    // Initialize timer used to refresh data in the table.
    /** @type {!angular.$q.Promise} */
    var refreshTimer = this.interval_(this.refreshData_.bind(this),
                                      this.autoRefreshInterval_);

    // Destroy the timer when the shared directive's scope is destroyed.
    this.scope_.$on('$destroy', function() {
      this.interval_.cancel(refreshTimer);
    }.bind(this));
  }

  // Whenever the filter changes, we need to refetch the items and start from
  // page 1.
  this.scope_.$watch(this.attrs_['filterValue'], this.onFilterChange_.bind(this));
};

var InfiniteTableController = exports.InfiniteTableController;


/** @const */
InfiniteTableController.DEFAULT_PAGE_SIZE = 50;


/** @const */
InfiniteTableController.LOADING_TEMPLATE = '<tr><td colspan="100" ' +
    'class="table-loading">Loading...</td></tr>';


/** @const */
InfiniteTableController.UNIQUE_KEY_NAME = '_grrTableKey';

/** @const */
InfiniteTableController.ROW_HASH_NAME = '_grrTableRowHash';


/**
 * Changes fetched items list, updating the presentation accordingly.
 *
 * @param {Array<Object>} newValue New version of fetched items.
 * @private
 */
InfiniteTableController.prototype.setFetchedItems_ = function(newValue) {
  if (newValue.length != this.fetchedItems_.length) {
    var loadingElement = $(this.rootElement_).find('tr:has(td.table-loading)');
    for (var i = this.fetchedItems_.length; i < newValue.length; ++i) {
      this.transclude_(
          function(clone, scope) {
            scope.item = newValue[i];

            var key = newValue[i][InfiniteTableController.UNIQUE_KEY_NAME];
            if (angular.isUndefined(key) && this.autoRefreshInterval_) {
              // Exceptions thrown inside transclude_() call will be swallowed,
              // using logging instead.
              this.log_.error('items in infinite table with auto-refresh ' +
                  'have to have ' + InfiniteTableController.UNIQUE_KEY_NAME +
                  ' set');
            }
            key = key || '';

            var rowHash = newValue[i][InfiniteTableController.ROW_HASH_NAME];
            if (angular.isUndefined(rowHash) && this.autoRefreshInterval_) {
              // Exceptions thrown inside transclude_() call will be swallowed,
              // using logging instead.
              this.log_.error('items in infinite table with auto-refresh ' +
                  'have to have ' + InfiniteTableController.ROW_HASH_NAME +
                  ' set');
            }
            rowHash = rowHash || '';

            // Put the new element between 2 comments, so that we can easily
            // find it. The way Angular works, a single transclude element
            // may expand itself into 2 or more elements, so it's not
            // enough to track the transcluded element itself, since more
            // siblings may be added later.
            //
            // Therefore we track the start/end comments and it's guaranteed
            // that all transcluded elements corresponding to the current
            // item will be between them.
            var startComment = document.createComment('-> ' + key);
            var endComment = document.createComment('<- ' + key);
            this.elementScopes_[key] = [
              startComment,
              endComment,
              scope,
              rowHash];

            $(startComment).insertBefore(loadingElement);
            clone.insertBefore(loadingElement);
            $(endComment).insertBefore(loadingElement);
          }.bind(this));
    }
  }

  this.fetchedItems_ = newValue;
};


/**
 * Triggers reload of all the elements. If multiple pages were fetched, they
 * will be fetched again (see showUntilPage). This function is assigned
 * to user-provided binding if trigger-update attribute is specified.
 *
 * @param {boolean} graceful If true, then do not reload, but rather update
 *     the table - i.e. trigger an immediate auto-refresh iteration.
 *     Auto-refresh doesn't delete old elements, it searches for changed
 *     items and updates them and inserts new items to the top of the table.
 *     User doesn't see the table reloading itself while auto-refresh is in
 *     progress.
 *
 * @export
 */
InfiniteTableController.prototype.triggerUpdate = function(graceful) {
  if (graceful) {
    if (!this.autoRefreshInterval_) {
      throw new Error('graceful refresh is only possible in infinite tables ' +
          'with auto-refresh turned on');
    }
    this.refreshData_();
  } else {
    // Make sure that in-flight requests' results will be ignored.
    this.updateCounter_++;
    // As we cancel the in-flight requests, it's safe to set these flag to false.
    this.loadingInProgress_ = false;
    this.autoRefreshInProgress_ = false;

    this.setFetchedItems_([]);
    this.currentPage_ = 0;
    this.rootElement_.html(InfiniteTableController.LOADING_TEMPLATE);
  }
};

/**
 * When the filter value changes, we need to get the items again and start
 * from the beginning.
 *
 * @param {string} newFilterValue The new filter value.
 * @private
 */
InfiniteTableController.prototype.onFilterChange_ = function(newFilterValue) {
  if (newFilterValue !== this.filterValue_) {
    this.filterValue_ = newFilterValue;
    this.triggerUpdate(false);
  }
};


/**
 * Checks if "table loading..." element is visible and calls
 * tableLoadingElementWasShown if it is.
 *
 * @private
 */
InfiniteTableController.prototype.checkIfTableLoadingIsVisible_ = function() {
  if (this.loadingInProgress_) {
    return;
  }

  $(this.rootElement_).find('.table-loading').each(
      function(index, loadingElement) {
        var loadingOffset = loadingElement.getBoundingClientRect();
        // NOTE: using Math.ceil here is important since elementFromPoint is
        // pixel-sensitive and effectively needs integer coordinates, while
        // getBoundClientRect is not - it returns floating-point coordinates
        // when zoom level is other than 100%.
        //
        // I.e. getBoundingClientRect may return position (30.9, 40.9)
        // while what we really want is (31, 41). We also have to add +1 to x
        // and y coordinates, since the bounding client rect returned by the
        // getBoundingClientRect() is an outer rectangle and the actual element
        // is positioned within it.
        var elem = document.elementFromPoint(
            Math.ceil(loadingOffset.left) + 1,
            Math.ceil(loadingOffset.top) + 1);

        if ($(elem).hasClass('table-loading')) {
          this.tableLoadingElementWasShown_();
        } else if (this.showUntilPage_ > this.currentPage_) {
          this.tableLoadingElementWasShown_();
        }
      }.bind(this));
};


/**
 * Starts a graceful-refresh. Refetches all items that are currently
 * shown and updates the elements or adds new ones to the beginning
 * of the list.
 *
 * @private
 */
InfiniteTableController.prototype.refreshData_ = function() {
  if (this.loadingInProgress_ || this.autoRefreshInProgress_) {
    return;
  }

  this.autoRefreshInProgress_ = true;

  var prevUpdateCounter = this.updateCounter_;
  this.itemsProvider.fetchItems(0, this.currentPage_ * this.pageSize_).then(
      function(newItems) {
        if (this.updateCounter_ === prevUpdateCounter) {
          this.autoRefreshInProgress_ = false;
          this.onAutoRefreshDataFetched_(newItems);
        }
      }.bind(this));
};

/**
 * Handles data fetched during periodic auto-refresh. Updates the elements
 * or adds new ones at the beginning of the table.
 *
 * @param {Object} newItems Server response with new items.
 *
 * @private
 */
InfiniteTableController.prototype.onAutoRefreshDataFetched_ = function(newItems) {
  for (var i = newItems.items.length - 1; i >= 0; --i) {
    var newItem = newItems.items[i];
    var key = newItem[InfiniteTableController.UNIQUE_KEY_NAME];
    var rowHash = newItem[InfiniteTableController.ROW_HASH_NAME];
    var elemScope = this.elementScopes_[key];

    if (angular.isDefined(elemScope)) {
      // The item with the same unique key was already displayed. We need to
      // remove the old element and show a new one.
      var startComment = elemScope[0];
      var endComment = elemScope[1];
      var scope = elemScope[2];
      var oldRowHash = elemScope[3];

      if (angular.equals(oldRowHash, rowHash)) {
        continue;
      }

      scope.$destroy();

      // Remove elements between startComment and endComment.
      var toRemove = [];
      for (var e = startComment.nextSibling; e !== endComment; e = e.nextSibling) {
        toRemove.push(e);
      }
      $(toRemove).remove();

      // Transclude new elements between the startComment and endComment.
      this.transclude_(
          function(clone, scope) {
            scope.item = newItem;
            this.elementScopes_[key] = [
              startComment,
              endComment,
              scope,
              rowHash];

            clone.insertBefore(endComment);
          }.bind(this));
    } else {
      // This is a new item, add it as a first row of the table.
      this.fetchedItems_.splice(0, 0, newItem);

      this.transclude_(
          function(clone, scope) {
            scope.item = newItem;

            var startComment = document.createComment('-> ' + key);
            var endComment = document.createComment('<- ' + key);
            this.elementScopes_[key] = [
              startComment,
              endComment,
              scope,
              rowHash];

            this.rootElement_.prepend([startComment, clone, endComment]);
          }.bind(this));
    }
  }
};

/**
 * Issues a request to the API service to fetch more data. Called when
 * "Table loading..." row becomes visible.
 *
 * @private
 */
InfiniteTableController.prototype.tableLoadingElementWasShown_ = function() {
  this.loadingInProgress_ = true;

  var prevUpdateCounter = this.updateCounter_;
  if (!this.filterValue_) {
    this.itemsProvider.fetchItems(
        this.currentPage_ * this.pageSize_,
        this.pageSize_).then(function(values) {
          if (this.updateCounter_ === prevUpdateCounter) {
            this.onItemsFetched_(values);
          }
        }.bind(this));
  } else {
    this.itemsProvider.fetchFilteredItems(
        this.filterValue_,
        this.currentPage_ * this.pageSize_,
        this.pageSize_).then(function(values) {
          if (this.updateCounter_ === prevUpdateCounter) {
            this.onItemsFetched_(values);
          }
        }.bind(this));
  }
};


/**
 * Adds freshly fetched items to the fetchedItems list and updates internal
 * state. Called when new data arrive from items provider.
 *
 * @param {!grrUi.core.itemsProviderController.Items} newlyFetchedItems
 * @private
 */
InfiniteTableController.prototype.onItemsFetched_ = function(
    newlyFetchedItems) {
  this.setFetchedItems_(this.fetchedItems_.concat(newlyFetchedItems.items));
  if (newlyFetchedItems.items.length == 0) {
    $(this.rootElement_).find('tr:has(.table-loading)').remove();
  }

  this.currentPage_ += 1;
  if (this.currentPage_ > this.showUntilPage_) {
    this.showUntilPage_ = this.currentPage_;
  }
  this.loadingInProgress_ = false;
};



/**
 * Displays tables that are "infinitely scrollable", i.e. they add elements to
 * the bottom on scrolling until they run out of data.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.InfiniteTableDirective = function() {
  return {
    transclude: 'element',
    restrict: 'A',
    priority: 1000,
    terminal: true,
    require: ['grrInfiniteTable',
              '?grrMemoryItemsProvider',
              '?grrApiItemsProvider'],
    controller: InfiniteTableController,
    link: function(scope, element, attrs, controllers) {
      var providerController = undefined;
      for (var i = 1; i < controllers.length; ++i) {
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

      controllers[0].itemsProvider = providerController;
    }
  };
};


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
exports.InfiniteTableDirective.directive_name = 'grrInfiniteTable';
