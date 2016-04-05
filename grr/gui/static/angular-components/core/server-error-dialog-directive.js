'use strict';

goog.provide('grrUi.core.serverErrorDialogDirective.ServerErrorDialogController');
goog.provide('grrUi.core.serverErrorDialogDirective.ServerErrorDialogDirective');

goog.scope(function() {


/**
 * Controller for ServerErrorDialogDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.core.serverErrorDialogDirective.ServerErrorDialogController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;
};

var ServerErrorDialogController =
  grrUi.core.serverErrorDialogDirective.ServerErrorDialogController;


/**
 * Directive for showing the error dialog.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.serverErrorDialogDirective.ServerErrorDialogDirective = function() {
  return {
    scope: {
      close: '&',
      message: '=',
      traceBack: '='
    },
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
grrUi.core.serverErrorDialogDirective.ServerErrorDialogDirective.directive_name =
  'grrServerErrorDialog';


});  // goog.scope
