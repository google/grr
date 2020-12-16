goog.module('grrUi.artifact.uploadArtifactDialogDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const artifactDescriptorsService = goog.requireType('grrUi.artifact.artifactDescriptorsService');



/**
 * Controller for UploadArtifactDialogController.
 * @unrestricted
 */
const UploadArtifactDialogController = class {
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

    /** @private {!angular.$q} */
    this.q_ = $q;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /**
     * @private {!artifactDescriptorsService.ArtifactDescriptorsService}
     */
    this.grrArtifactDescriptorsService_ = grrArtifactDescriptorsService;

    /** @export {?string} */
    this.artifact = null;

    /** @export {boolean} */
    this.inProgress = false;
  }

  /**
   * Sends /label/add request to the server.
   *
   * @param {!FileList} files Value of the input[type=file].
   * @export
   */
  onFileSet(files) {
    this.scope_.$apply(() => {
      const reader = new FileReader();
      reader.onload = (event) => {
        this.artifact = event.target.result;
      };
      reader.readAsText(files[0], 'UTF-8');
    });
  }

  /**
   * Sends /artifacts/upload request to the server with an attached
   * artifact file.
   *
   * @return {!angular.$q.Promise} A promise indicating success or failure.
   * @export
   */
  proceed() {
    var deferred = this.q_.defer();

    this.inProgress = true;
    this.grrApiService_
        .post('/artifacts', {'artifact': this.artifact}, false, {})
        .then(
            function success() {
              deferred.resolve('Artifact was successfully uploaded.');
              this.grrArtifactDescriptorsService_.clearCache();
            }.bind(this),
            function failure(response) {
              deferred.reject(response.data.message);
            }.bind(this));

    return deferred.promise;
  }
};



/**
 * Directive that displays "artifact upload" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.UploadArtifactDialogDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/artifact/' +
        'upload-artifact-dialog.html',
    controller: UploadArtifactDialogController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.UploadArtifactDialogDirective.directive_name =
    'grrUploadArtifactDialog';
