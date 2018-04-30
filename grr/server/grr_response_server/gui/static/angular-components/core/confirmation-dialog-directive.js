'use strict';

goog.module('grrUi.core.confirmationDialogDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ConfirmationDialogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$timeout} $timeout
 * @ngInject
 */
const ConfirmationDialogController =
  function($scope, $timeout) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.$timeout} */
    this.timeout_ = $timeout;

    /** @export {?string} */
    this.error;

    /** @export {?string} */
    this.success;
  };



/**
 * Calls the proceed function provided in the scope.
 *
 * @export
 */
ConfirmationDialogController.prototype.proceed = function() {
  var result = this.scope_.proceed();
  if(result){
    result.then(function success(successMessage) {
      this.success = successMessage;

      if (this.scope_['autoCloseOnSuccess']) {
        this.timeout_(function() {
          this.close();
        }.bind(this), 1000);
      }
    }.bind(this), function failure(errorMessage) {
      this.error = errorMessage;
    }.bind(this));
  }
};

/**
 * AngularJS UI attaches a $dismiss method to the modal scope. Since the modal scope
 * is a potentially indirect parent of the current scope, we need to search for
 * the method in the scope hierarchy.
 *
 * @export
 */
ConfirmationDialogController.prototype.dismiss = function() {
  var curScope = this.scope_;
  while (curScope && !curScope['$dismiss']) {
    curScope = curScope.$parent;
  }
  if (curScope) {
    curScope['$dismiss']();
  }
};

/**
 * AngularJS UI attaches a $close method to the modal scope. Since the modal scope
 * is a potentially indirect parent of the current scope, we need to search for
 * the method in the scope hierarchy.
 *
 * @export
 */
ConfirmationDialogController.prototype.close = function() {
  var curScope = this.scope_;
  while (curScope && !curScope['$close']) {
    curScope = curScope.$parent;
  }
  if (curScope) {
    curScope['$close']();
  }
};

/**
 * Directive that displays a confirmation dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.ConfirmationDialogDirective = function() {
  return {
    scope: {
      title: '=',
      closeName: '=',
      cancelName: '=',
      proceedName: '=',
      proceedClass: '=',
      proceed: '&',
      canProceed: '&?',
      autoCloseOnSuccess: '='
    },
    restrict: 'E',
    transclude: true,
    templateUrl: '/static/angular-components/core/confirmation-dialog.html',
    controller: ConfirmationDialogController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.ConfirmationDialogDirective.directive_name = 'grrConfirmationDialog';
