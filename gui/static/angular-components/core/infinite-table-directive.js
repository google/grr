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
 * @param {!angular.JQLite} $element
 * @param {!angular.$interval} $interval
 * @param {function(function(angular.JQLite, angular.Scope), angular.JQLite)}
 *     $transclude
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

  /** @private {!angular.JQLite} */
  this.element_ = $element;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {function(function(angular.JQLite, angular.Scope),
      angular.JQLite)} */
  this.transclude_ = $transclude;

  /** @private {!angular.$parse} */
  this.parse_ = $parse;

  // Internal state.

  /**
   * Items provider to be used for fetching items to be displayed.
   * @export {!grrUi.core.itemsProviderController.ItemsProviderController}
   */
  this.itemsProvider;

  /**
   * List of currently fetched items.
   * @export {!Array.<Object>}
   */
  this.fetchedItems = [];

  /**
   * Current page index. Used when calculating ranges of items to be fetched.
   * @export {number}
   */
  this.currentPage = 0;

  /**
   * If this is bigger than currentPage, new pages of data will be fetched
   * until currentPage == showUntilPage.
   * @export {number}
   */
  this.showUntilPage = 0;

  /**
   * True, if there's a request currently in progress.
   * @export {boolean}
   */
  this.requestInProgress = false;

  /**
   * Root element where all the rendered data will be appended to.
   * @export {angular.JQLite}
   */
  this.rootElement = this.element_.parent();

  /**
   * Page size - if not specified by the user, defaults to 50.
   * @export {number}
   */
  this.pageSize = Number($scope.$eval(this.attrs_.pageSize)) ||
      this.DEFAULT_PAGE_SIZE;

  /**
   * This directive does not have an isolated scope, but it creates an inner
   * scope (in order not to polute the shared one) to register watchers.
   * @export {!angular.Scope}
   */
  this.innerScope = this.scope_.$new(true);

  this.innerScope.controller = this;
  this.innerScope.$watchCollection('controller.fetchedItems',
                                   this.onFetchedItemsChange_.bind(this));

  // Replace the directive's element with table-loading row.
  var template = angular.element('<tr ' +
      '><td class="table-loading">Loading...</td></tr>');
  this.element_.replaceWith(template);

  // If triggerUpdate attribute is defined, assign own triggerUpdate function
  // to it. This way users of the directive will be able to trigger updates.
  if (angular.isDefined(this.attrs_.triggerUpdate)) {
    var parsedExpression = $parse(this.attrs_.triggerUpdate);
    parsedExpression.assign(this.scope_, this.triggerUpdate.bind(this));
  }

  // Initialize timer used to check whether table-loading element is visible.

  // TODO(user): JSCompiler type checking thinks that timer may become
  // null for some reason, although $interval definition clearly states
  // that it can't. Turning off the type checking here to prevent
  // compiler from complaining.
  /** @type {?} */
  var timer = this.interval_(this.checkIfTableLoadingIsVisible_.bind(this),
                             100);

  // Destroy the timer when inner scope is destroyed.
  this.innerScope.$on('$destroy', function() {
    this.interval_.cancel(timer);
  }.bind(this));

  // Destroy the inner scope when the shared directive's scope is destroyed.
  this.scope_.$on('$destroy', function() {
    this.innerScope.$destroy();
  }.bind(this));
};

var InfiniteTableController =
    grrUi.core.infiniteTableDirective.InfiniteTableController;


/** @const */
InfiniteTableController.prototype.DEFAULT_PAGE_SIZE = 50;


/**
 * Handles fetchedItems changes.
 *
 * @param {Array<Object>} newValue New version of fetched items.
 * @param {Array<Object>} oldValue Old version of fetched items.
 * @private
 */
InfiniteTableController.prototype.onFetchedItemsChange_ = function(
    newValue, oldValue) {
  var oldLength;
  if (angular.isUndefined(oldValue)) {
    oldLength = 0;
  } else {
    oldLength = oldValue.length;
  }

  if (newValue.length !== oldLength) {
    var loadingElement = $(this.rootElement).find('tr:has(td.table-loading)');
    for (var i = oldLength; i < newValue.length; ++i) {
      this.transclude_(
          function(clone, scope) {
            scope.item = newValue[i];
            clone.insertBefore(loadingElement);
          }, this.rootElement);
    }
  }
};


/**
 * Triggers reload of all the elements. If multiple pages were fetched, they
 * will be fetched again (see showUntilPage). This function is assigned
 * to user-provided binding if trigger-update attribute is specified.
 *
 * @export
 */
InfiniteTableController.prototype.triggerUpdate = function() {
  this.fetchedItems = [];
  this.currentPage = 0;
  this.rootElement.html('<tr ' +
      '><td class="table-loading">Loading...</td></tr>');
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
        } else if (this.showUntilPage > self.currentPage) {
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
  this.itemsProvider.fetchItems(
      this.currentPage * this.pageSize, this.pageSize).then(
      this.onItemsFetched_.bind(this));
};


/**
 * Adds freshly fetched items to the fetchedItems list and updates internal
 * state. Called when new data arrive from items provider.
 *
 * @param {Array<Object>} newlyFetchedItems
 * @private
 */
InfiniteTableController.prototype.onItemsFetched_ = function(
    newlyFetchedItems) {
  this.fetchedItems = this.fetchedItems.concat(newlyFetchedItems);
  if (newlyFetchedItems.length === 0) {
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
              '?grrApiItemsProvider',
              '?grrAff4ItemsProvider'],
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
grrUi.core.infiniteTableDirective.InfiniteTableDirective.
    directive_name = 'grrInfiniteTable';

});  // goog.scope
