'use strict';

goog.provide('grrUi.core.apiService.ApiService');
goog.provide('grrUi.core.apiService.encodeUrlPath');
goog.provide('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {


/**
 * URL-encodes url path (URL-encodes all non-allowed characters except
 * for forward slashes ('/'). Must be used since user-provided data
 * may be used as parts of urls (file paths, for example, are used
 * in virtual file system URLs).
 *
 * @param {string} urlPath Source url path.
 * @return {string} Encoded url path.
 */
grrUi.core.apiService.encodeUrlPath = function(urlPath) {
  var components = urlPath.split('/');
  var encodedComponents = components.map(encodeURIComponent);
  return encodedComponents.join('/');
};
var encodeUrlPath = grrUi.core.apiService.encodeUrlPath;

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
grrUi.core.apiService.stripTypeInfo = function(richlyTypedValue) {
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
var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;


/**
 * Service for doing GRR API calls.
 *
 * @param {angular.$http} $http The Angular http service.
 * @param {!angular.$q} $q
 * @param {!angular.$interval} $interval
 * @param {grrUi.core.loadingIndicatorService.LoadingIndicatorService} grrLoadingIndicatorService
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.apiService.ApiService = function(
    $http, $q, $interval, grrLoadingIndicatorService) {
  /** @private {angular.$http} */
  this.http_ = $http;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {grrUi.core.loadingIndicatorService.LoadingIndicatorService} */
  this.grrLoadingIndicatorService_ = grrLoadingIndicatorService;
};
var ApiService = grrUi.core.apiService.ApiService;


/**
 * Name of the service in Angular.
 */
ApiService.service_name = 'grrApiService';

/**
 * Fetches data for a given API url via the specified HTTP method.
 *
 * @param {string} method The HTTP method to use, e.g. HEAD, GET, etc.
 * @param {string} apiPath API path to trigger/
 * @param {Object<string, string>=} opt_params Query parameters.
 * @param {Object<string, string>=} opt_requestSettings Request settings
 *     (cache, etc).
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 * @private
 */
ApiService.prototype.sendRequest_ = function(method, apiPath, opt_params,
                                             opt_requestSettings) {
  var requestParams = angular.extend({}, opt_params);
  if (grr.state.reason) {
    requestParams.reason = grr.state.reason;
  }

  var requestSettings = angular.extend({}, opt_requestSettings);

  var loadingKey = this.grrLoadingIndicatorService_.startLoading();
  var url = encodeUrlPath('/api/' + apiPath.replace(/^\//, ''));

  var promise = /** @type {function(Object)} */ (this.http_)({
    method: method,
    url: url,
    params: requestParams,
    cache: requestSettings['cache']
  });

  return promise.finally(function() {
    this.grrLoadingIndicatorService_.stopLoading(loadingKey);
  }.bind(this));
};

/**
 * Fetches data for a given API url via HTTP HEAD method.
 *
 * @param {string} apiPath API path to trigger/
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.head = function(apiPath, opt_params) {
  return this.sendRequest_("HEAD", apiPath, opt_params);
};

/**
 * Fetches data for a given API url via HTTP GET method.
 *
 * @param {string} apiPath API path to trigger/
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.get = function(apiPath, opt_params) {
  return this.sendRequest_("GET", apiPath, opt_params);
};

/**
 * Fetches data for a given API url via HTTP GET method.
 *
 * @param {string} apiPath API path to trigger/
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.getCached = function(apiPath, opt_params) {
  return this.sendRequest_("GET", apiPath, opt_params, {cache: true});
};

/**
 * Deletes the resource behind a given API url via HTTP DELETE method.
 *
 * @param {string} apiPath API path to trigger/
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.delete = function(apiPath, opt_params) {
  return this.sendRequest_("DELETE", apiPath, opt_params);
};

/**
 * Initiates a file download via HTTP GET method.
 *
 * @param {string} apiPath API path to trigger/
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the download status.
 */
ApiService.prototype.downloadFile = function(apiPath, opt_params) {
  var requestParams = angular.extend({}, opt_params);
  var url = encodeUrlPath('/api/' + apiPath.replace(/^\//, ''));

  // Using HEAD to check that there are no ACL issues when accessing url
  // in question.
  return this.http_.head(url, { params: requestParams }).then(function () {
    // If HEAD request succeeds, initiate the download via an iFrame.
    var paramsString = Object.keys(requestParams).sort().map(function(key) {
      return [key, requestParams[key]].map(encodeURIComponent).join("=");
    }).join("&");
    if (paramsString.length > 0) {
      url += '?' + paramsString;
    }

    var deferred = this.q_.defer();

    var iframe = document.createElement('iframe');
    iframe.src = url;
    document.body.appendChild(iframe);

    var intervalPromise = this.interval_(function() {
      try {
        if (iframe.contentWindow.document.readyState === 'complete') {
          this.interval_.cancel(intervalPromise);
          deferred.resolve();
        }
      } catch (err) {
        // If iframe loading fails, it displays an error page which we don't
        // have an access to (same origin policy). We use this condition to
        // detect when iframe loading fails and reject the promise with a
        // stub response object.
        deferred.reject({
          data: {
            message: 'Unknown error.'
          }
        });
      }
    }.bind(this), 500);

    return deferred.promise.finally(function() {
      this.interval_.cancel(intervalPromise);
    }.bind(this));

  }.bind(this), function failure(response) {
    if (response.status == 403) {
      var headers = response.headers();
      // HEAD resposne is not expected to have any body. Therefore using
      // headers to get failure subject and reason information.
      // TODO(user): Refactor handling of 403 errors in the Angular
      // way.
      grr.publish('unauthorized', headers['x-grr-unauthorized-access-subject'],
                  headers['x-grr-unauthorized-access-reason']);
    }

    // If HEAD request fails, propagate the failure.
    return this.q_.reject(response);
  }.bind(this));
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
    opt_params = /** @type {Object<string, string>} */ (stripTypeInfo(
        opt_params));
  }

  var request;
  if (angular.equals(opt_files || {}, {})) {
    request = {
      method: 'POST',
      url: encodeUrlPath('/api/' + apiPath.replace(/^\//, '')),
      data: opt_params,
      headers: {}
    };
  } else {
    var fd = new FormData();
    angular.forEach(/** @type {Object} */(opt_files), function(value, key) {
      fd.append(key, value);
    }.bind(this));
    fd.append('_params_', angular.toJson(opt_params || {}));

    request = {
      method: 'POST',
      url: encodeUrlPath('/api/' + apiPath.replace(/^\//, '')),
      data: fd,
      transformRequest: angular.identity,
      headers: {
        'Content-Type': undefined
      }
    };
  }

  if (grr.state.reason) {
    request.headers['X-GRR-REASON'] = encodeURIComponent(grr.state.reason);
  }

  var loadingKey = this.grrLoadingIndicatorService_.startLoading();
  var promise = /** @type {function(Object)} */ (this.http_)(request);
  return promise.finally(function() {
    this.grrLoadingIndicatorService_.stopLoading(loadingKey);
  }.bind(this));
};

});  // goog.scope
