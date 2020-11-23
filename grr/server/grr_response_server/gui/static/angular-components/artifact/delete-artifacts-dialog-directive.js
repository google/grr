goog.module('grrUi.artifact.deleteArtifactsDialogDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const artifactDescriptorsService = goog.requireType('grrUi.artifact.artifactDescriptorsService');



/**
 * Controller for DeleteArtifactsDialogController.
 * @unrestricted
 */
const DeleteArtifactsDialogController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.$q} $q
   * @param {!apiService.ApiService} grrApiService
   * @param {!artifactDescriptorsService.ArtifactDescriptorsService}
   *     grrArtifactDescriptorsService
   * @ngInject
   */
  constructor($scope, $q, grrApiService, grrArtifactDescriptorsService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /**
     * @private {!artifactDescriptorsService.ArtifactDescriptorsService}
     */
    this.grrArtifactDescriptorsService_ = grrArtifactDescriptorsService;

    /** @private {!angular.$q} */
    this.q_ = $q;
  }

  /**
   * Sends /artifacts/delete request to the server.
   *
   * @return {!angular.$q.Promise} A promise indicating success or failure.
   * @export
   */
  proceed() {
    var deferred = this.q_.defer();

    this.grrApiService_.delete('/artifacts', {names: this.scope_['names']})
        .then(
            function success() {
              deferred.resolve('Artifacts were deleted successfully.');
              this.grrArtifactDescriptorsService_.clearCache();
            }.bind(this),
            function failure(response) {
              deferred.reject(response.data.message);
            }.bind(this));

    return deferred.promise;
  }
};



/**
 * Directive that displays "artifact delete" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.DeleteArtifactsDialogDirective = function() {
  return {
    scope: {names: '='},
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
exports.DeleteArtifactsDialogDirective.directive_name =
    'grrDeleteArtifactsDialog';
