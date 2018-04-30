'use strict';

goog.module('grrUi.core.apiService');
goog.module.declareLegacyNamespace();



var UNAUTHORIZED_API_RESPONSE_EVENT = 'UnauthorizedApiResponse';

/**
 * "Refresh folder" event name.
 * @const
 */
exports.UNAUTHORIZED_API_RESPONSE_EVENT = UNAUTHORIZED_API_RESPONSE_EVENT;

/**
 * URL-encodes url path (URL-encodes all non-allowed characters except
 * for forward slashes ('/'). Must be used since user-provided data
 * may be used as parts of urls (file paths, for example, are used
 * in virtual file system URLs).
 *
 * @param {string} urlPath Source url path.
 * @return {string} Encoded url path.
 */
exports.encodeUrlPath = function(urlPath) {
  var components = urlPath.split('/');
  var encodedComponents = components.map(encodeURIComponent);
  return encodedComponents.join('/');
};
var encodeUrlPath = exports.encodeUrlPath;

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
exports.stripTypeInfo = function(richlyTypedValue) {
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
var stripTypeInfo = exports.stripTypeInfo;


/**
 * Wraps a promise so that then/catch/finally calls preserve the custom
 * cancel() method.
 *
 * @param {!angular.$q.Promise} promise Cancelable promise to wrap.
 * @return {!angular.$q.Promise} Wrapped promise. Its then/catch/finally
 *     methods will propagate 'cancel' property of the parent promise to
 *     children promises.
 */
var wrapCancellablePromise_ = function(promise) {
  var cancel = promise['cancel'];

  if (angular.isUndefined(promise['_oldThen'])) {
    promise['_oldThen'] = promise['then'];
    promise['then'] = function(onFulfilled, onRejected, progressBack) {
      var result = promise['_oldThen'](
          onFulfilled, onRejected, progressBack);
      result['cancel'] = cancel;
      return wrapCancellablePromise_(result);
    };
  }

  if (angular.isUndefined(promise['_oldCatch'])) {
    promise['_oldCatch'] = promise['catch'];
    promise['catch'] = function(callback) {
      var result = promise['_oldCatch'](callback);
      result['cancel'] = cancel;
      return wrapCancellablePromise_(result);
    };
  }

  if (angular.isUndefined(promise['_oldFinally'])) {
    promise['_oldFinally'] = promise['finally'];
    promise['finally'] = function(callback, progressBack) {
      var result = promise['_oldFinally'](callback, progressBack);
      result['cancel'] = cancel;
      return wrapCancellablePromise_(result);
    };
  }

  return promise;
};


/**
 * Service for doing GRR API calls.
 *
 * @param {angular.$http} $http The Angular http service.
 * @param {!angular.$q} $q
 * @param {!angular.$interval} $interval
 * @param {angular.Scope} $rootScope The Angular root scope.
 * @param {!grrUi.core.loadingIndicatorService.LoadingIndicatorService} grrLoadingIndicatorService
 * @constructor
 * @ngInject
 * @export
 */
exports.ApiService = function(
    $http, $q, $interval, $rootScope, grrLoadingIndicatorService) {
  /** @private {angular.$http} */
  this.http_ = $http;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {grrUi.core.loadingIndicatorService.LoadingIndicatorService} */
  this.grrLoadingIndicatorService_ = grrLoadingIndicatorService;

  /** @private {!angular.$q.Deferred} */
  this.authDeferred_ = this.q_.defer();
};
var ApiService = exports.ApiService;


/**
 * Name of the service in Angular.
 */
ApiService.service_name = 'grrApiService';


/**
 * Executes a given function only when authentication setup was done (i.e. after
 * markAuthDone was called).
 *
 * @param {function()} fn Callback to be called when authentication is done.
 * @return {!angular.$q.Promise} Promise that will be resolved with a callback
 *     return value after the authentication setup is done.
 * @private
 */
ApiService.prototype.waitForAuth_ = function(fn) {
  return this.authDeferred_.promise.then(function() {
    return fn();
  });
};

/**
 * This marks authentication setup as done, immediately resolving all promises
 * created by ApiService calls and blocked on the authentication setup.
 *
 * @export
 */
ApiService.prototype.markAuthDone = function() {
  this.authDeferred_.resolve();
};


/**
 * Fetches data for a given API url via the specified HTTP method.
 *
 * @param {string} method The HTTP method to use, e.g. HEAD, GET, etc.
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Query parameters.
 * @param {Object<string, string>=} opt_requestSettings Request settings
 *     (cache, etc).
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 * @private
 */
ApiService.prototype.sendRequestWithoutPayload_ = function(
    method, apiPath, opt_params, opt_requestSettings) {
  var requestParams = angular.extend({}, opt_params);
  var requestSettings = angular.extend({}, opt_requestSettings);

  var loadingKey = this.grrLoadingIndicatorService_.startLoading();
  var apiPrefix = '/api/';
  if (requestSettings['useV2']) {
    apiPrefix += 'v2/';
  }
  var url = encodeUrlPath(apiPrefix + apiPath.replace(/^\//, ''));

  return this.waitForAuth_(function() {
    var promise = /** @type {function(Object)} */ (this.http_)({
      method: method,
      url: url,
      params: requestParams,
      cache: requestSettings['cache']
    });

    return promise.finally(function() {
      this.grrLoadingIndicatorService_.stopLoading(loadingKey);
    }.bind(this));
  }.bind(this));
};

/**
 * Fetches data for a given API url via HTTP HEAD method.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.head = function(apiPath, opt_params) {
  return this.sendRequestWithoutPayload_("HEAD", apiPath, opt_params);
};

/**
 * Fetches data for a given API url via HTTP GET method.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.get = function(apiPath, opt_params) {
  return this.sendRequestWithoutPayload_("GET", apiPath, opt_params);
};


/**
 * Fetches data for a given API url via HTTP GET method.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.getV2 = function(apiPath, opt_params) {
  return this.sendRequestWithoutPayload_("GET", apiPath, opt_params, {'useV2': true});
};

/**
 * Fetches data for a given API url via HTTP GET method and caches the response.
 * Returns cached response immediately (without querying the server),
 * if available.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.getCached = function(apiPath, opt_params) {
  return this.sendRequestWithoutPayload_("GET", apiPath, opt_params,
                                         {cache: true});
};


/**
 * Fetches data for a given API url via HTTP GET method and caches the response.
 * Returns cached response immediately (without querying the server),
 * if available.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Query parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.getV2Cached = function(apiPath, opt_params) {
  return this.sendRequestWithoutPayload_("GET", apiPath, opt_params,
                                         {cache: true, useV2: true});
};


/**
 * Polls a given URL every second until the given condition is satisfied
 * (if opt_checkFn is undefined, meaning no condition was provided, then
 * the condiition is having JSON responses's 'state' attribute being
 * equal to 'FINISHED').
 *
 * @param {string} apiPath API path to trigger.
 * @param {number} intervalMs Interval between polls in milliseconds.
 * @param {Object<string, string>=} opt_params Query parameters.
 * @param {Function=} opt_checkFn Function that checks if
 *     polling can be stopped. Default implementation checks for operation
 *     status to be "FINISHED" (response.data.status == 'FINISHED').
 * @return {!angular.$q.Promise} Promise that resolves to the HTTP response
 *     for which checkFn() call returned true or to the first failed
 *     HTTP response (with status code != 200).
 */
ApiService.prototype.poll = function(apiPath, intervalMs, opt_params,
                                     opt_checkFn) {
  if (angular.isUndefined(opt_checkFn)) {
    opt_checkFn = function(response) {
      return response['data']['state'] === 'FINISHED';
    }.bind(this);
  }

  var result = this.q_.defer();
  var inProgress = false;
  var cancelled = false;
  var pollIteration = function() {
    inProgress = true;
    this.get(apiPath, opt_params).then(function success(response) {
      if (cancelled) {
        return;
      }
      result.notify(response);

      if (opt_checkFn(response)) {
        result.resolve(response);
      }
    }.bind(this), function failure(response) {
      if (cancelled) {
        return;
      }
      result.reject(response);
    }.bind(this)).finally(function() {
      if (cancelled) {
        return;
      }
      inProgress = false;
    }.bind(this));
  }.bind(this);

  pollIteration();

  var intervalPromise = this.interval_(function() {
    if (!inProgress) {
      pollIteration();
    }
  }.bind(this), intervalMs);

  result.promise['cancel'] = function() {
    cancelled = true;
    this.interval_.cancel(intervalPromise);
  }.bind(this);
  result.promise.finally(result.promise['cancel']);

  return wrapCancellablePromise_(result.promise);
};

/**
 * Cancels polling previously started by poll(). As a result of this
 * the promise will neither be resolved, nor rejected.
 *
 * @param {!angular.$q.Promise|undefined} pollPromise Promise returned by
 *     poll() call.
 */
ApiService.prototype.cancelPoll = function(pollPromise) {
  if (angular.isDefined(pollPromise)) {
    if (angular.isUndefined(pollPromise['cancel'])) {
      throw new Error('Invalid promise to cancel: not cancelable.');
    }
    pollPromise['cancel']();
  }
};

/**
 * Initiates a file download via HTTP GET method.
 *
 * @param {string} apiPath API path to trigger.
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
      // HEAD response is not expected to have any body. Therefore using
      // headers to get failure subject and reason information.
      var headers = response.headers();
      this.rootScope_.$broadcast(
          UNAUTHORIZED_API_RESPONSE_EVENT,
          {
            subject: headers['x-grr-unauthorized-access-subject'],
            reason: headers['x-grr-unauthorized-access-reason']
          });
    }

    // If HEAD request fails, propagate the failure.
    return this.q_.reject(response);
  }.bind(this));
};


/**
 * Sends request with a payload (POST/PATCH/DELETE) to the server.
 *
 * @param {string} httpMethod HTTP method to use.
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Dictionary that will be
        sent as a POST payload.
 * @param {boolean=} opt_stripTypeInfo If true, treat opt_params as JSON-encoded
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
 *
 * @private
 */
ApiService.prototype.sendRequestWithPayload_ = function(
    httpMethod, apiPath, opt_params, opt_stripTypeInfo, opt_files) {
  if (opt_stripTypeInfo) {
    opt_params = /** @type {Object<string, string>} */ (stripTypeInfo(
        opt_params));
  }

  var request;
  if (angular.equals(opt_files || {}, {})) {
    request = {
      method: httpMethod,
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
      method: httpMethod,
      url: encodeUrlPath('/api/' + apiPath.replace(/^\//, '')),
      data: fd,
      transformRequest: angular.identity,
      headers: {
        'Content-Type': undefined
      }
    };
  }

  return this.waitForAuth_(function() {
    var loadingKey = this.grrLoadingIndicatorService_.startLoading();
    var promise = /** @type {function(Object)} */ (this.http_)(request);
    return promise.finally(function() {
      this.grrLoadingIndicatorService_.stopLoading(loadingKey);
    }.bind(this));
  }.bind(this));
};


/**
 * Sends POST request to the server.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Dictionary that will be
        sent as a POST payload.
 * @param {boolean=} opt_stripTypeInfo If true, treat opt_params as JSON-encoded
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
  return this.sendRequestWithPayload_(
      'POST', apiPath, opt_params, opt_stripTypeInfo, opt_files);
};


/**
 * Deletes the resource behind a given API url via HTTP DELETE method.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Dictionary that will be
        sent as a DELETE payload.
 * @param {boolean=} opt_stripTypeInfo If true, treat opt_params as JSON-encoded
 *      RDFValue with rich type information. This type information
 *      will be stripped before opt_params is sent as a POST payload.
 *
 *      This option is useful when sending values edited with forms back to the
 *      server. Values edited by semantic forms will have rich type information
 *      in them, while server will be expecting stripped down version of the
 *      same data. See stripTypeInfo() documentation for an example.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.delete = function(apiPath, opt_params, opt_stripTypeInfo) {
  return this.sendRequestWithPayload_(
      'DELETE', apiPath, opt_params, opt_stripTypeInfo);
};


/**
 * Patches the resource behind a given API url via HTTP PATCH method.
 *
 * @param {string} apiPath API path to trigger.
 * @param {Object<string, string>=} opt_params Dictionary that will be
        sent as a UDATE payload.
 * @param {boolean=} opt_stripTypeInfo If true, treat opt_params as JSON-encoded
 *      RDFValue with rich type information. This type information
 *      will be stripped before opt_params is sent as a POST payload.
 *
 *      This option is useful when sending values edited with forms back to the
 *      server. Values edited by semantic forms will have rich type information
 *      in them, while server will be expecting stripped down version of the
 *      same data. See stripTypeInfo() documentation for an example.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 */
ApiService.prototype.patch = function(apiPath, opt_params, opt_stripTypeInfo) {
  return this.sendRequestWithPayload_(
      'PATCH', apiPath, opt_params, opt_stripTypeInfo);
};
