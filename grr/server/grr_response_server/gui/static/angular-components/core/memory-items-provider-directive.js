'use strict';

goog.module('grrUi.core.memoryItemsProviderDirective');
goog.module.declareLegacyNamespace();

const {Items, ItemsProviderController} = goog.require('grrUi.core.itemsProviderController');



/**
 * Controller for MemoryItemsProviderDirective.
 *
 * @constructor
 * @implements {ItemsProviderController}
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!angular.Attributes} $attrs
 * @param {!angular.$parse} $parse
 *
 * @ngInject
 */
exports.MemoryItemsProviderController = function($scope, $q, $attrs, $parse) {
  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {Array<?>} */
  this.items_;

  if (angular.isUndefined($attrs.items)) {
    throw new Error('"items" attribute has to be specified.');
  }

  // aff4Path is a traditional double-way binding.
  $scope.$watch($attrs.items, function() {
    this.items_ = /** @type {Array<?>} */ ($scope.$eval($attrs.items));
  }.bind(this));
};

var MemoryItemsProviderController = exports.MemoryItemsProviderController;


/**
 * Fetches specified number of collection items starting from a given offset.
 *
 * @param {number} offset Items will be fetched from collection starting at
 *     this offset.
 * @param {number} count Number of items to be fetched.
 * @param {boolean=} opt_withTotalCount if true, total number of elements in
 *     the collection will be returned along with fetched items.
 * @return {!angular.$q.Promise} Fetched items promise. Resolves to
 *     grrUi.core.itemsProviderController.Items. If opt_withTotalCount
 *     was set to true, resulting object will have totalCount attribute
 *     containing total number of items in the collection on the server.
 */
MemoryItemsProviderController.prototype.fetchItems = function(
    offset, count, opt_withTotalCount) {
  if (angular.isUndefined(opt_withTotalCount)) {
    opt_withTotalCount = false;
  }

  var items = this.items_;
  var deferred = this.q_.defer();

  var resultItems = items.slice(offset, offset + count);

  /** @type {Items} */
  var result = {
    offset: offset,
    items: resultItems
  };
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
 * @return {!angular.$q.Promise} Fetched items. Resolves to
 *     grrUi.core.itemsProviderController.Items.
 */
MemoryItemsProviderController.prototype.fetchFilteredItems = function(
    filter, offset, count) {
  filter = filter.toLowerCase();

  var items = this.items_;
  var deferred = this.q_.defer();

  var filteredItems = [];
  angular.forEach(items, function(item) {
    if (JSON.stringify(item).toLowerCase().indexOf(filter) != -1) {
      filteredItems.push(item);
    }
  });

  filteredItems = filteredItems.slice(offset, offset + count);

  /** @type {Items} */
  var result = {
    offset: offset,
    items: filteredItems
  };


  deferred.resolve(result);
  return deferred.promise;
};



/**
 * Directive setting up memory data provider for table directives. This
 * directive is designed to be used in tests in the first place, in
 * conjunction with grr-paged-filtered-table and grr-infinite-table
 * directives.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.MemoryItemsProviderDirective = function() {
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
exports.MemoryItemsProviderDirective.directive_name = 'grrMemoryItemsProvider';
