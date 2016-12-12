'use strict';

goog.provide('grrUi.core.serverErrorInterceptorFactory.ServerErrorInterceptorFactory');
goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');

goog.scope(function() {

var ERROR_EVENT_NAME = grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.error_event_name;
var INTERCEPTED_STATUS_CODES = [500];


/**
 * Checks if a response needs to be intercepted.
 *
 * @param {{status: number}} response
 * @return {boolean} Whether interception is needed or not.
 * @private
 */
grrUi.core.serverErrorInterceptorFactory.needsInterception_ = function(response) {
  return INTERCEPTED_STATUS_CODES.indexOf(response.status) !== -1;
};

/**
 * Creates a server error object
 *
 * @param {{data: {message: string, traceBack: string}}} response
 * @return {{message: string, traceBack: string}} A server error object
 * @private
 */
grrUi.core.serverErrorInterceptorFactory.extractError_ = function(response) {
  var data = response.data || {};
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
grrUi.core.serverErrorInterceptorFactory.ServerErrorInterceptorFactory = function($rootScope, $q) {
  return {
    responseError: function(response) {
      if(grrUi.core.serverErrorInterceptorFactory.needsInterception_(response)) {
        var error = grrUi.core.serverErrorInterceptorFactory.extractError_(response);
        $rootScope.$broadcast(ERROR_EVENT_NAME, error);
      }
      return $q.reject(response);
    }
  };
};

var ServerErrorInterceptorFactory =
  grrUi.core.serverErrorInterceptorFactory.ServerErrorInterceptorFactory;


/**
 * Factory's name in Angular.
 *
 * @const
 * @export
 */
ServerErrorInterceptorFactory.factory_name = 'grrServerErrorInterceptorFactory';


});
