'use strict';

goog.provide('grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogController');
goog.provide('grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective');


goog.scope(function() {


/**
 * Controller for DeleteArtifactsDialogController.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.artifact.artifactDescriptorsService.ArtifactDescriptorsService} grrArtifactDescriptorsService
 * @ngInject
 */
grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogController = function(
    $scope, $q, grrApiService, grrArtifactDescriptorsService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.artifact.artifactDescriptorsService.ArtifactDescriptorsService} */
  this.grrArtifactDescriptorsService_ = grrArtifactDescriptorsService;

  /** @private {!angular.$q} */
  this.q_ = $q;
};

var DeleteArtifactsDialogController =
  grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogController;


/**
 * Sends /artifacts/delete request to the server.
 *
 * @return {!angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
DeleteArtifactsDialogController.prototype.proceed = function() {
  var deferred = this.q_.defer();

  this.grrApiService_.delete(
      '/artifacts', { names: this.scope_['names'] }).then(
        function success() {
          deferred.resolve('Artifacts were deleted successfully.');
          this.grrArtifactDescriptorsService_.clearCache();
        }.bind(this),
        function failure(response) {
          deferred.reject(response.data.message);
        }.bind(this));

  return deferred.promise;
};


/**
 * Directive that displays "artifact delete" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective = function() {
  return {
    scope: {
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
