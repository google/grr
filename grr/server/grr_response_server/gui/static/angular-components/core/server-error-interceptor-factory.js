goog.module('grrUi.core.serverErrorInterceptorFactory');

const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');



const ERROR_EVENT_NAME = ServerErrorButtonDirective.error_event_name;
const INTERCEPTED_STATUS_CODES = [500];


/**
 * Checks if a response needs to be intercepted.
 *
 * @param {{status: number}} response
 * @return {boolean} Whether interception is needed or not.
 * @private
 */
const needsInterception_ = function(response) {
  return INTERCEPTED_STATUS_CODES.indexOf(response.status) !== -1;
};

/**
 * Creates a server error object
 *
 * @param {{data: {message: string, traceBack: string}}} response
 * @return {{message: string, traceBack: string}} A server error object
 * @private
 */
const extractError_ = function(response) {
  const data = response.data || {};
  return {
    message: data.message || 'Unknown Server Error',
    traceBack: data.traceBack
  };
};


/**
 * Controller for ServerErrorDialogDirective.
 *
 * @param {!angular.Scope} $rootScope
 * @param {!angular.$q} $q
 * @return {*} Server error interceptor.
 * @constructor
 * @ngInject
 */
exports.ServerErrorInterceptorFactory = function($rootScope, $q) {
  return {
    responseError: function(response) {
      if (needsInterception_(response)) {
        const error = extractError_(response);
        $rootScope.$broadcast(ERROR_EVENT_NAME, error);
      }
      return $q.reject(response);
    }
  };
};

const ServerErrorInterceptorFactory = exports.ServerErrorInterceptorFactory;


/**
 * Factory's name in Angular.
 *
 * @const
 * @export
 */
ServerErrorInterceptorFactory.factory_name = 'grrServerErrorInterceptorFactory';
