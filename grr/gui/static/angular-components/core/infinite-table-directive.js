'use strict';

goog.provide('grrUi.core.infiniteTableDirective.InfiniteTableController');
goog.provide('grrUi.core.infiniteTableDirective.InfiniteTableDirective');


goog.scope(function() {


/**
 * Controller for InfiniteTableDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.Attributes} $attrs
 * @param {!angular.jQuery} $element
 * @param {!angular.$interval} $interval
 * @param {function(function(angular.jQuery, angular.Scope), angular.jQuery)} $transclude
 * @param {!angular.$parse} $parse
 * @ngInject
 */
grrUi.core.infiniteTableDirective.InfiniteTableController = function(
    $scope, $attrs, $element, $interval, $transclude, $parse) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.Attributes} */
  this.attrs_ = $attrs;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /**
   * @private {function(function(angular.jQuery, angular.Scope),
   *     angular.jQuery)}
   */
  this.transclude_ = $transclude;

  // Internal state.

  /**
   * Items provider to be used for fetching items to be displayed.
   * @export {grrUi.core.itemsProviderController.ItemsProviderController}
   */
  this.itemsProvider;

  /**
   * List of currently fetched items.
   * @export {!Array<Object>}
   */
  this.fetchedItems = [];

  /**
   * Current page index. Used when calculating ranges of items to be fetched.
   * @export {number}
   */
  this.currentPage = 0;

  /**
   * If this is bigger than currentPage, new pages of data will be fetched
   * until currentPage == showUntilPage (currentPage gets incremented every
   * time a new page is fetched). This mechanism is used when triggerUpdate
   * is called, so that same amount of data is displayed after the update.
   * @export {number}
   */
  this.showUntilPage = 0;

  /**
   * @export {string}
   */
  this.filterValue;

  /**
   * True, if there's a request currently in progress.
   * @export {boolean}
   */
  this.requestInProgress = false;

  /**
   * Root element where all the rendered data will be appended to.
   * @export {angular.jQuery}
   */
  this.rootElement = this.element_.parent();

  /**
   * Page size - if not specified by the user, defaults to 50.
   * @export {number}
   */
  this.pageSize = Number($scope.$eval(this.attrs_['pageSize'])) ||
      InfiniteTableController.DEFAULT_PAGE_SIZE;

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
  var timer = this.interval_(this.checkIfTableLoadingIsVisible_.bind(this),
                             100);

  // Destroy the timer when the shared directive's scope is destroyed.
  this.scope_.$on('$destroy', function() {
    this.interval_.cancel(timer);
  }.bind(this));

  // Whenever the filter changes, we need to refetch the items and start from
  // page 1.
  this.scope_.$watch(this.attrs_['filterValue'], this.onFilterChange_.bind(this));
};

var InfiniteTableController =
    grrUi.core.infiniteTableDirective.InfiniteTableController;


/** @const */
InfiniteTableController.DEFAULT_PAGE_SIZE = 50;


/** @const */
InfiniteTableController.LOADING_TEMPLATE = '<tr><td colspan="100" ' +
    'class="table-loading">Loading...</td></tr>';


/**
 * Changes fetched items list, updating the presentation accordingly.
 *
 * @param {Array<Object>} newValue New version of fetched items.
 * @private
 */
InfiniteTableController.prototype.setFetchedItems_ = function(newValue) {
  if (newValue.length != this.fetchedItems.length) {
    var loadingElement = $(this.rootElement).find('tr:has(td.table-loading)');
    for (var i = this.fetchedItems.length; i < newValue.length; ++i) {
      this.transclude_(
          function(clone, scope) {
            scope.item = newValue[i];
            clone.insertBefore(loadingElement);
          }, this.rootElement);
    }
  }

  this.fetchedItems = newValue;
};


/**
 * Triggers reload of all the elements. If multiple pages were fetched, they
 * will be fetched again (see showUntilPage). This function is assigned
 * to user-provided binding if trigger-update attribute is specified.
 *
 * @export
 */
InfiniteTableController.prototype.triggerUpdate = function() {
  this.setFetchedItems_([]);
  this.currentPage = 0;
  this.rootElement.html(InfiniteTableController.LOADING_TEMPLATE);
};

/**
 * When the filter value changes, we need to get the items again and start
 * from the beginning.
 *
 * @param {string} newFilterValue The new filter value.
 * @private
 */
InfiniteTableController.prototype.onFilterChange_ = function(newFilterValue) {
  if (newFilterValue !== this.filterValue) {
    this.filterValue = newFilterValue;
    this.triggerUpdate();
  }
};


/**
 * Checks if "table loading..." element is visible and calls
 * tableLoadingElementWasShown if it is.
 *
 * @private
 */
InfiniteTableController.prototype.checkIfTableLoadingIsVisible_ = function() {
  if (this.requestInProgress) {
    return;
  }

  $(this.rootElement).find('.table-loading').each(
      function(index, loadingElement) {
        var loadingOffset = $(loadingElement).offset();
        var elem = document.elementFromPoint(
            loadingOffset.left - $(window).scrollLeft() + 1,
            loadingOffset.top - $(window).scrollTop() + 1);
        if ($(elem).hasClass('table-loading')) {
          this.tableLoadingElementWasShown_();
        } else if (this.showUntilPage > this.currentPage) {
          this.tableLoadingElementWasShown_();
        }
      }.bind(this));
};


/**
 * Issues a request to the API service to fetch more data. Called when
 * "Table loading..." row becomes visible.
 *
 * @private
 */
InfiniteTableController.prototype.tableLoadingElementWasShown_ = function() {
  this.requestInProgress = true;
  if (!this.filterValue) {
    this.itemsProvider.fetchItems(
        this.currentPage * this.pageSize,
        this.pageSize).then(this.onItemsFetched_.bind(this));
  } else {
    this.itemsProvider.fetchFilteredItems(
        this.filterValue,
        this.currentPage * this.pageSize,
        this.pageSize).then(this.onItemsFetched_.bind(this));
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
  this.setFetchedItems_(this.fetchedItems.concat(newlyFetchedItems.items));
  if (newlyFetchedItems.items.length == 0 ||
      newlyFetchedItems.items.length < this.pageSize) {
    $(this.rootElement).find('tr:has(.table-loading)').remove();
  }

  this.currentPage += 1;
  if (this.currentPage > this.showUntilPage) {
    this.showUntilPage = this.currentPage;
  }
  this.requestInProgress = false;
};



/**
 * Displays tables that are "infinitely scrollable", i.e. they add elements to
 * the bottom on scrolling until they run out of data.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.infiniteTableDirective.InfiniteTableDirective = function() {
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
grrUi.core.infiniteTableDirective.InfiniteTableDirective
    .directive_name = 'grrInfiniteTable';

});  // goog.scope
