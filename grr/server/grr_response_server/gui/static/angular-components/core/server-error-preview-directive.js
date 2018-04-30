'use strict';

goog.module('grrUi.core.serverErrorPreviewDirective');
goog.module.declareLegacyNamespace();

const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');



var ERROR_EVENT_NAME =
  ServerErrorButtonDirective.error_event_name;

var ERROR_PREVIEW_INTERVAL = 5000; //ms


/**
 * Controller for ServerErrorPreviewDirective.
 *
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!angular.$timeout} $timeout
 * @constructor
 * @ngInject
 */
const ServerErrorPreviewController = function($rootScope, $scope, $timeout) {

  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$timeout} */
  this.timeout_ = $timeout;

  /** @type {?{message: string, traceBack: string}} */
  this.error;

  /** @type {boolean} */
  this.labelVisible;

  this.rootScope_.$on(ERROR_EVENT_NAME, this.onErrorEvent.bind(this));
};



/**
 * Handles server error events
 *
 * @param {?} unused_event The event object
 * @param {{message: string, traceBack: string}} error The server error
 */
ServerErrorPreviewController.prototype.onErrorEvent = function(unused_event, error) {
  if (!angular.isObject(error) || !angular.isString(error.message)) {
    return;
  }

  if (error.message.length) {
    this.error = error;
    this.labelVisible = true;

    // hide error preview after ERROR_PREVIEW_INTERVAL ms.
    this.timeout_(function() {
      this.labelVisible = false;
    }.bind(this), ERROR_PREVIEW_INTERVAL);
  } else {
    this.error = null;
    this.labelVisible = false;
  }
};


/**
 * Directive that displays a label with the error message whenever a server
 * error occurs
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ServerErrorPreviewDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    replace: true,
    template: '<div class="navbar-text" ng-show="controller.labelVisible">' +
    '    {$ controller.error.message $}' +
    '</div>',
    controller: ServerErrorPreviewController,
    controllerAs: 'controller'
  };
};

var ServerErrorPreviewDirective = exports.ServerErrorPreviewDirective;

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
ServerErrorPreviewDirective.directive_name = 'grrServerErrorPreview';

/**
 * The duration of how long the preview is visible.
 *
 * @const
 * @export
 */
ServerErrorPreviewDirective.error_preview_interval = 5000;


