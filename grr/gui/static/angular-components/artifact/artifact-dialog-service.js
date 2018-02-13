'use strict';

goog.module('grrUi.artifact.artifactDialogService');
goog.module.declareLegacyNamespace();

const {DeleteArtifactsDialogDirective} = goog.require('grrUi.artifact.deleteArtifactsDialogDirective');
const {UploadArtifactDialogDirective} = goog.require('grrUi.artifact.uploadArtifactDialogDirective');



/**
 * Service for artifacts dialogs.
 *
 * @param {grrUi.core.dialogService.DialogService} grrDialogService
 * @constructor
 * @ngInject
 * @export
 */
exports.ArtifactDialogService = function(grrDialogService) {
  /** @private {grrUi.core.dialogService.DialogService} */
  this.grrDialogService_ = grrDialogService;
};

var ArtifactDialogService = exports.ArtifactDialogService;


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
ArtifactDialogService.prototype.openDeleteArtifacts = function(names) {
  var directive = DeleteArtifactsDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name, { names: names });
};

/**
 * Shows an upload artifact dialog.
 *
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
ArtifactDialogService.prototype.openUploadArtifact = function() {
  var directive = UploadArtifactDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name);
};
