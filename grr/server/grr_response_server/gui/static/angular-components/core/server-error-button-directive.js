'use strict';

goog.module('grrUi.core.serverErrorButtonDirective');
goog.module.declareLegacyNamespace();



var ERROR_EVENT_NAME = 'ServerError';


/**
 * Controller for ServerErrorButtonDirective.
 *
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
 * @constructor
 * @ngInject
 */
const ServerErrorButtonController = function($rootScope, $scope, $uibModal) {

  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$uibModal} */
  this.uibModal_ = $uibModal;

  /** @type {?{message: string, traceBack: string}} */
  this.error;

  /** @type {boolean} */
  this.buttonVisible;


  this.rootScope_.$on(ERROR_EVENT_NAME, this.onErrorEvent.bind(this));
};



/**
 * Handles server error events
 *
 * @param {?} unused_event The event object
 * @param {{message: string, traceBack: string}} error The server error
 */
ServerErrorButtonController.prototype.onErrorEvent = function(unused_event, error) {
  if (!angular.isObject(error) || !angular.isString(error.message)) {
    return;
  }

  if (error.message.length) {
    this.error = error;
    this.buttonVisible = true;
  } else {
    this.error = null;
    this.buttonVisible = false;
  }
};

/**
 * Shows the server error in a dialog.
 *
 * @export
 */
ServerErrorButtonController.prototype.showError = function() {
  var modalScope = this.scope_.$new();
  modalScope.message = this.error.message;
  modalScope.traceBack = this.error.traceBack;
  modalScope.close = function() {
    modalInstance.close();
  };
  this.scope_.$on('$destroy', function() {
    modalScope.$destroy();
  });

  var modalInstance = this.uibModal_.open({
    template: '<grr-server-error-dialog close="close()" message="message" trace-back="traceBack" />',
    scope: modalScope,
    windowClass: 'wide-modal high-modal',
    size: 'lg'
  });

  modalInstance.result.finally(function() {
    this.error = null;
    this.buttonVisible = false;
  }.bind(this));
};


/**
 * Directive that displays a button whenever a server error occurs
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ServerErrorButtonDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    replace: true,
    templateUrl: '/static/angular-components/core/server-error-button.html',
    controller: ServerErrorButtonController,
    controllerAs: 'controller'
  };
};

var ServerErrorButtonDirective = exports.ServerErrorButtonDirective;

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
ServerErrorButtonDirective.directive_name = 'grrServerErrorButton';

/**
 * Name of the server error event
 *
 * @const
 * @export
 */
ServerErrorButtonDirective.error_event_name = ERROR_EVENT_NAME;


