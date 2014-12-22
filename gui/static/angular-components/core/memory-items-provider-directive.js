'use strict';

goog.provide('grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderController');
goog.provide('grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderDirective');
goog.require('grrUi.core.itemsProviderController.ItemsProviderController');

goog.scope(function() {



/**
 * Controller for MemoryItemsProviderDirective.
 *
 * @constructor
 * @implements {grrUi.core.itemsProviderController.ItemsProviderController}
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!angular.Attributes} $attrs
 * @param {!angular.$parse} $parse
 *
 * @ngInject
 */
grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderController =
    function($scope, $q, $attrs, $parse) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {Array<?>} */
  this.items_;

  if (angular.isUndefined($attrs.items)) {
    throw new Error('"items" attribute has to be specified.');
  }

  // aff4Path is a traditional double-way binding.
  $scope.$watch($attrs.items, function() {
    this.items_ = $scope.$eval($attrs.items);
  }.bind(this));
};

var MemoryItemsProviderController =
    grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderController;


/**
 * Fetches specified number of collection items starting from a given offset.
 *
 * @param {number} offset Items will be fetched from collection starting at
 *     this offset.
 * @param {number} count Number of items to be fetched.
 * @param {boolean=} opt_withTotalCount if true, total number of elements in
 *     the collection will be returned along with fetched items.
 * @return {!angular.$q.Promise} Fetched items promise. If opt_withTotalCount
 *     was set to true, resulting array will have totalCount attribute
 *     containing total number of items in the collection on the server.
 */
MemoryItemsProviderController.prototype.fetchItems = function(
    offset, count, opt_withTotalCount) {
  if (angular.isUndefined(opt_withTotalCount)) {
    opt_withTotalCount = false;
  }

  var items = this.items_;
  var deferred = this.q_.defer();

  var result = items.slice(offset, offset + count);
  if (opt_withTotalCount) {
    result.totalCount = items.length;
  }

  deferred.resolve(result);
  return deferred.promise;
};


/**
 * Fetches specified number of collection items filtered by a given token
 * starting from a given offset.
 *
 * @param {string} filter Token to be used for filtering.
 * @param {number} offset Number of items to skip in the resulting set.
 * @param {number} count Maximum number of items to be returned.
 * @return {!angular.$q.Promise} Fetched items.
 */
MemoryItemsProviderController.prototype.fetchFilteredItems = function(
    filter, offset, count) {

  var items = this.items_;
  var deferred = this.q_.defer();

  var filteredItems = [];
  angular.forEach(items, function(item) {
    if (JSON.stringify(item).indexOf(filter) != -1) {
      filteredItems.push(item);
    }
  });

  deferred.resolve(filteredItems.slice(offset, offset + count));
  return deferred.promise;
};



/**
 * Directive setting up memory data provider for table directives. This
 * directive is designed to be used in tests in the first place, in
 * conjunction with grr-paged-filtered-table and grr-infinite-table
 * directives.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderDirective =
    function() {
  return {
    restrict: 'A',
    priority: 2000,
    controller: MemoryItemsProviderController
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderDirective.
    directive_name = 'grrMemoryItemsProvider';

});  // goog.scope
