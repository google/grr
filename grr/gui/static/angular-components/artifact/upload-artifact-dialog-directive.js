'use strict';

goog.provide('grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogController');
goog.provide('grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective');


goog.scope(function() {


/**
 * Controller for UploadArtifactDialogController.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogController =
    function($scope, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.file;

  /** @export {boolean} */
  this.inProgress = false;

  /** @export {?string} */
  this.error;

  /** @export {?string} */
  this.success;
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
 * @export
 */
UploadArtifactDialogController.prototype.proceed = function() {
  this.inProgress = true;

  this.grrApiService_.post(
      '/artifacts/upload', {}, false, {'artifact': this.file}).then(
          function success() {
            this.success = 'Artifact was successfully uploaded.';
          }.bind(this),
          function failure(response) {
            this.error = response.data.message;
          }.bind(this));
};


/**
 * Directive that displays "artifact upload" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective =
    function() {
      return {
        scope: {
          dismiss: '&',
          close: '&'
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
