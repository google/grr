'use strict';

goog.provide('grrUi.core.aff4Service.Aff4Service');

goog.scope(function() {



/**
 * Service for querying AFF4 objects.
 *
 * @param {angular.$http} $http The Angular http service.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.aff4Service.Aff4Service = function($http) {
  /** @private {angular.$http} */
  this.http_ = $http;
};
var Aff4Service = grrUi.core.aff4Service.Aff4Service;


/**
 * Name of the service in Angular.
 */
Aff4Service.service_name = 'grrAff4Service';


/**
 * Converts given aff4path to a string that's usable as part of the
 * URL.
 *
 * @private
 * @param {string} aff4Path Aff4 path.
 * @return {string} URL-friendly Aff4 path.
 */
Aff4Service.prototype.processAff4Path_ = function(aff4Path) {
  return aff4Path.replace(/^aff4:\//, '').replace(/\/$/, '');
};


/**
 * Fetches data for object at the given AFF4 path using given params.
 *
 * @param {string} aff4Path AFF4 path to the object.
 * @param {Object?} params Dictionary with query parameters.
 * @return {angular.$q.Promise} Angular's promise that will resolve to
 *                             server's response.
 */
Aff4Service.prototype.get = function(aff4Path, params) {
  var requestParams = angular.extend({}, params);
  if (grr.state.reason) {
    requestParams.reason = grr.state.reason;
  }

  // TODO(user): implement this in angular way (i.e. - make a service).
  angular.element('#ajax_spinner').html(
      '<img src="/static/images/ajax-loader.gif">');
  var promise = this.http_.get('/api/aff4/' + this.processAff4Path_(aff4Path), {
    params: requestParams
  });
  return promise.then(function(response) {
    angular.element('#ajax_spinner').html('');
    return response;
  });
};

});  // goog.scope
