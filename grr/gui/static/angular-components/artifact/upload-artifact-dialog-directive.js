'use strict';

goog.provide('grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogController');
goog.provide('grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective');


goog.scope(function() {


/**
 * Controller for UploadArtifactDialogController.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogController = function($scope, $q, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.file;

  /** @export {boolean} */
  this.inProgress = false;
};

var UploadArtifactDialogController =
    grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogController;


/**
 * Sends /label/add request to the server.
 *
 * @param {Array<File>} files Value of the input[type=file].
 * @export
 */
UploadArtifactDialogController.prototype.onFileSet = function(files) {
  this.scope_.$apply(function() {
    this.file = files[0];
  }.bind(this));
};

/**
 * Sends /artifacts/upload request to the server with an attached
 * artifact file.
 *
 * @return {!angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
UploadArtifactDialogController.prototype.proceed = function() {
  var deferred = this.q_.defer();

  this.inProgress = true;
  this.grrApiService_.post(
    '/artifacts/upload', {}, false, {'artifact': this.file}).then(
      function success() {
        deferred.resolve('Artifact was successfully uploaded.');
      }.bind(this),
      function failure(response) {
        deferred.reject(response.data.message);
      }.bind(this));

  return deferred.promise;
};


/**
 * Directive that displays "artifact upload" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective = function() {
  return {
    scope: {
    },
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
grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective
    .directive_name = 'grrUploadArtifactDialog';


});
