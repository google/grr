'use strict';

goog.provide('grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderController');
goog.provide('grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderDirective');
goog.require('grrUi.core.itemsProviderController.ItemsProviderController');

goog.scope(function() {



/**
 * Controller for Aff4ItemsProviderDirective.
 *
 * @constructor
 * @implements {grrUi.core.itemsProviderController.ItemsProviderController}
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.Attributes} $attrs
 * @param {!angular.$parse} $parse
 * @param {!grrUi.core.aff4Service.Aff4Service} grrAff4Service
 *
 * @ngInject
 */
grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderController = function(
    $scope, $attrs, $parse, grrAff4Service) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.aff4Service.Aff4Service} */
  this.grrAff4Service_ = grrAff4Service;


  // Internal state.

  /**
   * Aff4-path to the collection where the items will be fetched from.
   * @export {string} aff4Path
   */
  this.aff4Path;

  /**
   * Optional query-params that will be passed to AFF4 api call.
   * @export {Object<string, string|number|boolean>}
   */
  this.queryParams;

  /**
   * If provided, all the fetched items will be passed through this function.
   * @export {?function(!angular.Scope, !Object)}
   */
  this.transformItems;


  // Aff4ItemsProvider directive has no isolated scope, so we have to
  // rely on $attrs, $eval and $parse to initialize the internal
  // state.

  // aff4Path is a traditional double-way binding.
  $scope.$watch($attrs.aff4Path, function() {
    this.aff4Path = /** @type {string} */ ($scope.$eval($attrs.aff4Path));
  }.bind(this));

  // queryParams is a traditional double-way binding.
  if ($attrs.queryParams) {
    $scope.$watch($attrs.queryParams, function() {
      this.queryParams = /** @type {Object<string, string|number|boolean>} */ (
          $scope.$eval($attrs.queryParams));
    }.bind(this));
  }

  // transformItems is a bound function call.
  if ($attrs.transformItems) {
    this.transformItems = /** @type {?function(!angular.Scope, !Object)} */ (
        $parse($attrs.transformItems));
  }
};

var Aff4ItemsProviderController =
    grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderController;


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
Aff4ItemsProviderController.prototype.fetchItems = function(
    offset, count, opt_withTotalCount) {
  if (angular.isUndefined(this.aff4Path)) {
    throw new Error("Can't fetch items: aff4 path not specified.");
  }

  if (angular.isUndefined(opt_withTotalCount)) {
    opt_withTotalCount = false;
  }

  var params = angular.extend(this.queryParams || {}, {
    'RDFValueCollection.offset': offset,
    'RDFValueCollection.count': count,
    'RDFValueCollection.with_total_count': opt_withTotalCount ? 1 : 0
  });

  return this.grrAff4Service_.get(this.aff4Path, params).then(
      this.onFetchedItems_.bind(this));
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
Aff4ItemsProviderController.prototype.fetchFilteredItems = function(
    filter, offset, count) {
  if (angular.isUndefined(this.aff4Path)) {
    throw new Error("Can't fetch filtered items: aff4 path not specified.");
  }

  var params = angular.extend(this.queryParams || {}, {
    'RDFValueCollection.filter': filter,
    'RDFValueCollection.offset': offset,
    'RDFValueCollection.count': count
  });

  return this.grrAff4Service_.get(this.aff4Path, params).then(
      this.onFetchedItems_.bind(this));
};


/**
 * Gets called as success callback of the AFF4 service promise.
 *
 * @param {Object} response Response object returned from the
server.
 * @return {!Array<Object>} Fetched collection items processed through
 *     tranformItems functions (if it was specified).
 * @private
 * @suppress {missingProperties} As response can be anything.
 */
Aff4ItemsProviderController.prototype.onFetchedItems_ = function(response) {
  var result = response.data.items;
  if (angular.isUndefined(result)) {
    result = [];
    result.totalCount = 0;
  }

  if (angular.isDefined(this.transformItems)) {
    result = this.transformItems(this.scope_, {'items': result});
    if (angular.isUndefined(result)) {
      throw new Error('transform-items function returned undefined');
    }
  }

  if (angular.isDefined(response.data.total_count)) {
    result.totalCount = response.data.total_count;
  }

  return result;
};



/**
 * Directive setting up AFF4 data provider for table directives.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderDirective = function() {
  return {
    restrict: 'A',
    priority: 2000,
    controller: Aff4ItemsProviderController
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderDirective.
    directive_name = 'grrAff4ItemsProvider';


});  // goog.scope
