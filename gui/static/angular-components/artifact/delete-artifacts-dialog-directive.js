'use strict';

goog.provide('grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogController');
goog.provide('grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective');


goog.scope(function() {


/**
 * Controller for DeleteArtifactsDialogController.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogController =
    function($scope, grrApiService) {
      /** @private {!angular.Scope} */
      this.scope_ = $scope;

      /** @private {!grrUi.core.apiService.ApiService} */
      this.grrApiService_ = grrApiService;

      /** @export {boolean} */
      this.inProgress = false;

      /** @export {?string} */
      this.error;

      /** @export {?string} */
      this.success;
    };
var DeleteArtifactsDialogController =
    grrUi.artifact.deleteArtifactsDialogDirective
    .DeleteArtifactsDialogController;


/**
 * Sends /artifacts/delete request to the server.
 *
 * @export
 */
DeleteArtifactsDialogController.prototype.proceed = function() {
  this.grrApiService_.post(
      '/artifacts/delete', {names: this.scope_.names}).then(
          function success() {
            this.success = 'Artifacts were deleted successfully.';
          }.bind(this),
          function failure(response) {
            this.error = response.data.message;
          }.bind(this));
};


/**
 * Directive that displays "artifact delete" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective =
    function() {
      return {
        scope: {
          dismiss: '&',
          close: '&',
          names: '='
        },
        restrict: 'E',
        templateUrl: '/static/angular-components/artifact/' +
            'delete-artifacts-dialog.html',
        controller: DeleteArtifactsDialogController,
        controllerAs: 'controller'
      };
    };


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective
    .directive_name = 'grrDeleteArtifactsDialog';


});
