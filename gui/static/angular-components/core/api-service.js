'use strict';

goog.provide('grrUi.core.apiService.ApiService');

goog.scope(function() {



/**
 * Service for doing GRR API calls.
 *
 * @param {angular.$http} $http The Angular http service.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.apiService.ApiService = function($http) {
  /** @private {angular.$http} */
  this.http_ = $http;
};
var ApiService = grrUi.core.apiService.ApiService;


/**
 * Name of the service in Angular.
 */
ApiService.service_name = 'grrApiService';


/**
 * Fetches data for a given API url.

 * @param {string} apiPath API path to triigger/
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.get = function(apiPath, opt_params) {
  var requestParams = angular.extend({}, opt_params);
  if (grr.state.reason) {
    requestParams.reason = grr.state.reason;
  }

  // TODO(user): implement this in angular way (i.e. - make a service).
  angular.element('#ajax_spinner').html(
      '<img src="/static/images/ajax-loader.gif">');

  var url = '/api/' + apiPath.replace(/^\//, '');
  var promise = this.http_.get(url, {
    params: requestParams
  });
  return promise.then(function(response) {
    angular.element('#ajax_spinner').html('');
    return response;
  });
};

});  // goog.scope
