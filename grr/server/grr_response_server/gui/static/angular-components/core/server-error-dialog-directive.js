goog.module('grrUi.core.serverErrorDialogDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ServerErrorDialogDirective.
 * @unrestricted
 */
const ServerErrorDialogController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;
  }
};



/**
 * Directive for showing the error dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ServerErrorDialogDirective = function() {
  return {
    scope: {close: '&', message: '=', traceBack: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/core/server-error-dialog.html',
    controller: ServerErrorDialogController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ServerErrorDialogDirective.directive_name = 'grrServerErrorDialog';
