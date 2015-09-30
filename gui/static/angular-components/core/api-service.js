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
 * Fetches data for a given API url via HTTP GET method.
 *
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


/**
 * Strips type information from a JSON-encoded RDFValue.
 * This may be useful when sending values edited with forms back to the
 * server. Values edited by semantic forms will have rich type information
 * in them, while server will be expecting stripped down version of the
 * same data.
 *
 * For example, this is the value that may be produced by the form:
 * {
 *     "age": 0,
 *     "mro": [
 *       "AFF4ObjectLabel",
 *       "RDFProtoStruct",
 *       "RDFStruct",
 *       "RDFValue",
 *       "object"
 *     ],
 *     "type": "AFF4ObjectLabel",
 *     "value": {
 *       "name": {
 *         "age": 0,
 *         "mro": [
 *           "unicode",
 *           "basestring",
 *           "object"
 *         ],
 *        "type": "unicode",
 *        "value": "label2"
 *       },
 *    }
 * }
 *
 * While the server expects this:
 * { "name": "label2" }
 *
 *
 * @param {*} richlyTypedValue JSON-encoded RDFValue with rich type information.
 * @return {*} Same RDFValue but with all type information stripped.
 */
ApiService.prototype.stripTypeInfo = function(richlyTypedValue) {
  var recursiveStrip = function(value) {
    if (angular.isArray(value)) {
      value = value.map(recursiveStrip);
    } else if (angular.isDefined(value.value)) {
      value = value.value;
      if (angular.isObject(value)) {
        for (var k in value) {
          value[k] = recursiveStrip(value[k]);
        }
      }
    }
    return value;
  };

  return recursiveStrip(angular.copy(richlyTypedValue));
};


/**
 * Sends POST request to the server.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Dictionary that will be
        sent as a POST payload.
 * @param {boolean} opt_stripTypeInfo If true, treat opt_params as JSON-encoded
 *      RDFValue with rich type information. This type information
 *      will be stripped before opt_params is sent as a POST payload.
 *
 *      This option is useful when sending values edited with forms back to the
 *      server. Values edited by semantic forms will have rich type information
 *      in them, while server will be expecting stripped down version of the
 *      same data. See stripTypeInfo() documentation for an example.
 * @param {Object<string, File>=} opt_files Dictionary with files to be uploaded
 *      to the server.
 *
 * @return {!angular.$q.Promise} Promise that resolves to the server response.
 */
ApiService.prototype.post = function(apiPath, opt_params, opt_stripTypeInfo,
                                     opt_files) {
  opt_params = opt_params || {};

  if (opt_stripTypeInfo) {
    opt_params = /** @type {Object<string, string>} */ (this.stripTypeInfo(
        opt_params));
  }

  // TODO(user): implement this in angular way (i.e. - make a service).
  angular.element('#ajax_spinner').html(
      '<img src="/static/images/ajax-loader.gif">');

  if (angular.equals(opt_files || {}, {})) {
    var request = {
      method: 'POST',
      url: '/api/' + apiPath.replace(/^\//, ''),
      data: opt_params
    };
    if (grr.state.reason) {
      request.headers = {
        'X-GRR-REASON': encodeURIComponent(grr.state.reason)
      };
    }

    var promise = /** @type {function(Object)} */ (this.http_)(request);
    return promise.then(function(response) {
      angular.element('#ajax_spinner').html('');
      return response;
    });
  } else {
    var fd = new FormData();
    angular.forEach(/** @type {Object} */(opt_files), function(value, key) {
      fd.append(key, value);
    }.bind(this));
    fd.append('_params_', angular.toJson(opt_params || {}));

    var request = {
      method: 'POST',
      url: '/api/' + apiPath.replace(/^\//, ''),
      data: fd,
      transformRequest: angular.identity,
      headers: {
        'Content-Type': undefined
      }
    };
    if (grr.state.reason) {
      request.headers['X-GRR-REASON'] = encodeURIComponent(grr.state.reason);
    }

    var promise = /** @type {function(Object)} */ (this.http_)(request);
    return promise.then(function(response) {
      angular.element('#ajax_spinner').html('');
      return response;
    });
  }
};


});  // goog.scope
