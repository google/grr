'use strict';

goog.module('grrUi.core.apiItemsProviderDirective');
goog.module.declareLegacyNamespace();

const {Items, ItemsProviderController} = goog.require('grrUi.core.itemsProviderController');



/**
 * Controller for ApiItemsProviderDirective..
 *
 * @constructor
 * @implements {ItemsProviderController}
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.Attributes} $attrs
 * @param {!angular.$parse} $parse
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!angular.$log} $log
 * @ngInject
 */
exports.ApiItemsProviderController = function(
    $scope, $attrs, $parse, grrApiService, $log) {

  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!angular.$log} */
  this.log_ = $log;

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
   * @export {?function(!angular.Scope, !Object):Array<?>}
   */
  this.transformItems;

  /**
   * If provided, all items will be fetched with the given HTTP method.
   * Defaults to GET.
   * @export {string}
   */
  this.method;

  // Aff4ItemsProvider directive has no isolated scope, so we have to
  // rely on $attrs, $eval and $parse to initialize the internal
  // state.

  // url is a traditional double-way binding.
  $scope.$watch($attrs['url'], function() {
    this.url = /** @type {string} */ ($scope.$eval($attrs['url']));
  }.bind(this));

  // queryParams is a traditional double-way binding.
  if ($attrs['queryParams']) {
    $scope.$watch($attrs['queryParams'], function() {
      this.queryParams = /** @type {Object<string, string|number|boolean>} */ (
          $scope.$eval($attrs['queryParams']));
    }.bind(this));
  }

  // transformItems is a bound function call.
  if ($attrs['transformItems']) {
    this.transformItems = /** @type {?function(!angular.Scope, !Object)} */ (
        $parse($attrs['transformItems']));
  }

  // transformItems is a bound function call.
  if ($attrs['method']) {
    this.method = /** @type {string} */ ($attrs['method']);
  }
};

var ApiItemsProviderController = exports.ApiItemsProviderController;


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
ApiItemsProviderController.prototype.fetchItems = function(
    offset, count, opt_withTotalCount) {
  var params = angular.extend(this.queryParams || {}, {
    'offset': offset,
    'count': count
  });

  if (this.method === 'POST') {
    return this.grrApiService_.post(this.url, params).then(
        this.onFetchedItems_.bind(this));
  } else {
    return this.grrApiService_.get(this.url, params).then(
        this.onFetchedItems_.bind(this));
  }
};


/**
 * Fetches specified number of collection items filtered by a given token
 * starting from a given offset. Assuming that API supports "filter"
 * parameter.
 *
 * @param {string} filter Token to be used for filtering.
 * @param {number} offset Number of items to skip in the resulting set.
 * @param {number} count Maximum number of items to be returned.
 * @return {!angular.$q.Promise} Fetched items. Resolves to
 *     grrUi.core.itemsProviderController.Items.
 */
ApiItemsProviderController.prototype.fetchFilteredItems = function(
    filter, offset, count) {
  var params = angular.extend(this.queryParams || {}, {
    'filter': filter,
    'offset': offset,
    'count': count
  });

  if (this.method === 'POST') {
    return this.grrApiService_.post(this.url, params).then(
        this.onFetchedItems_.bind(this));
  } else {
    return this.grrApiService_.get(this.url, params).then(
        this.onFetchedItems_.bind(this));
  }
};


/**
 * Gets called as success callback of the AFF4 service promise.
 *
 * @param {Object} response Response object returned from the server.
 * @return {*} Fetched items object processed through tranformItems
 *     function (if it was specified).
 * @private
 * @suppress {missingProperties} As response can be anything.
 */
ApiItemsProviderController.prototype.onFetchedItems_ = function(response) {
  /** @type {!Items} */
  var result = {
    items: response.data['items'] || [],
    offset: response.data['offset']
  };

  if (angular.isDefined(response.data['total_count'])) {
    result.totalCount = response.data['total_count'];
  }

  if (angular.isDefined(result.items) &&
      angular.isDefined(this.transformItems)) {

    try {
      result.items = this.transformItems(this.scope_,
                                         {'items': result.items});
    } catch (e) {
      this.log_.error('transformItems (on url ' + this.url +
                      ') failed: ' + e);
      throw e;
    }
    if (angular.isUndefined(result.items)) {
      var errorStr = 'transform-items function returned undefined';
      this.log_.error(errorStr);
      throw new Error(errorStr);
    }
  }

  return result;
};



/**
 * Directive setting up data provider for infinite table directive.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ApiItemsProviderDirective = function() {
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
exports.ApiItemsProviderDirective.directive_name = 'grrApiItemsProvider';
