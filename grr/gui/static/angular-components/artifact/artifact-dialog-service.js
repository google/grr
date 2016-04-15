'use strict';

goog.provide('grrUi.artifact.artifactDialogService.ArtifactDialogService');
goog.require('grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective');
goog.require('grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective');

goog.scope(function() {


/**
 * Service for artifacts dialogs.
 *
 * @param {grrUi.core.dialogService.DialogService} grrDialogService
 * @constructor
 * @ngInject
 * @export
 */
grrUi.artifact.artifactDialogService.ArtifactDialogService =
  function (grrDialogService) {
    /** @private {grrUi.core.dialogService.DialogService} */
    this.grrDialogService_ = grrDialogService;
  };

var ArtifactDialogService =
    grrUi.artifact.artifactDialogService.ArtifactDialogService;


/**
 * Name of the service in Angular.
 */
ArtifactDialogService.service_name = 'grrArtifactDialogService';

/**
 * Shows a delete artifact dialog.
 *
 * @param {Array<string>} names The names of the artifacts to delete.
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
ArtifactDialogService.prototype.openDeleteArtifacts = function(names){
  var directive = grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name, { names: names });
};

/**
 * Shows an upload artifact dialog.
 *
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
ArtifactDialogService.prototype.openUploadArtifact = function(){
  var directive = grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name);
};


});