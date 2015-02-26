'use strict';

goog.provide('grrUi.core.apiItemsProviderDirective.ApiItemsProviderController');
goog.provide('grrUi.core.apiItemsProviderDirective.ApiItemsProviderDirective');
goog.require('grrUi.core.itemsProviderController.ItemsProviderController');

goog.scope(function() {



/**
 * Controller for ApiItemsProviderDirective..
 *
 * @constructor
 * @implements {grrUi.core.itemsProviderController.ItemsProviderController}
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.Attributes} $attrs
 * @param {!angular.$parse} $parse
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 *
 * @ngInject
 */
grrUi.core.apiItemsProviderDirective.ApiItemsProviderController = function(
    $scope, $attrs, $parse, grrApiService) {

  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  // Internal state.

  /**
   * Url where the items are to be fetched from.
   * @export {string} url
   */
  this.url;

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

  // url is a traditional double-way binding.
  $scope.$watch($attrs.url, function() {
    this.url = /** @type {string} */ ($scope.$eval($attrs.url));
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

var ApiItemsProviderController =
    grrUi.core.apiItemsProviderDirective.ApiItemsProviderController;


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
ApiItemsProviderController.prototype.fetchItems = function(
    offset, count, opt_withTotalCount) {
  var params = angular.extend(this.queryParams || {}, {
    'offset': offset,
    'count': count
  });

  return this.grrApiService_.get(this.url, params).then(
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
ApiItemsProviderController.prototype.fetchFilteredItems = function(
    filter, offset, count) {
  throw new Error('Not implemented.');
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
ApiItemsProviderController.prototype.onFetchedItems_ = function(response) {
  var result;
  if (angular.isUndefined(response.data) ||
      angular.isUndefined(response.data.items)) {
    result = [];
  } else {
    result = response.data.items;
  }

  if (angular.isDefined(this.transformItems)) {
    result = this.transformItems(this.scope_, {'items': result});
    if (angular.isUndefined(result)) {
      throw new Error('transform-items function returned undefined');
    }
  }

  return result;
};



/**
 * Directive setting up data provider for infinite table directive.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.apiItemsProviderDirective.ApiItemsProviderDirective = function() {
  return {
    restrict: 'A',
    priority: 2000,
    controller: ApiItemsProviderController
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.apiItemsProviderDirective.ApiItemsProviderDirective.directive_name =
    'grrApiItemsProvider';


});  // goog.scope
