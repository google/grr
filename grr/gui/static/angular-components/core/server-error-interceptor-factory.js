'use strict';

goog.provide('grrUi.core.serverErrorInterceptorFactory.ServerErrorInterceptorFactory');
goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');

goog.scope(function() {

var ERROR_EVENT_NAME = grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.error_event_name;
var INTERCEPTED_STATUS_CODES = [500];
var module = grrUi.core.serverErrorInterceptorFactory;


/**
 * Checks if a response needs to be intercepted.
 *
 * @param {{status: number}} response
 * @private
 */
module.needsInterception_ = function(response) {
  return INTERCEPTED_STATUS_CODES.indexOf(response.status) !== -1;
};

/**
 * Creates a server error object
 *
 * @param {{data: {message: string, traceBack: string}}} response
 * @return {{message: string, traceBack: string}} A server error object
 * @private
 */
module.extractError_ = function(response) {
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
 * @constructor
 * @ngInject
 */
module.ServerErrorInterceptorFactory = function($rootScope, $q) {
  return {
    responseError: function(response) {
      if(module.needsInterception_(response)) {
        var error = module.extractError_(response);
        $rootScope.$broadcast(ERROR_EVENT_NAME, error);
      }
      return $q.reject(response);
    }
  };
};

var ServerErrorInterceptorFactory =
  module.ServerErrorInterceptorFactory;


/**
 * Factory's name in Angular.
 *
 * @const
 * @export
 */
ServerErrorInterceptorFactory.factory_name = 'grrServerErrorInterceptorFactory';


});
