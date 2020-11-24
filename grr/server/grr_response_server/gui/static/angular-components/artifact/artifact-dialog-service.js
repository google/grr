goog.module('grrUi.artifact.artifactDialogService');
goog.module.declareLegacyNamespace();

const dialogService = goog.requireType('grrUi.core.dialogService');
const {DeleteArtifactsDialogDirective} = goog.require('grrUi.artifact.deleteArtifactsDialogDirective');
const {UploadArtifactDialogDirective} = goog.require('grrUi.artifact.uploadArtifactDialogDirective');



/**
 * Service for artifacts dialogs.
 * @export
 * @unrestricted
 */
exports.ArtifactDialogService = class {
  /**
   * @param {dialogService.DialogService} grrDialogService
   * @ngInject
   */
  constructor(grrDialogService) {
    /** @private {dialogService.DialogService} */
    this.grrDialogService_ = grrDialogService;
  }

  /**
   * Shows a delete artifact dialog.
   *
   * @param {Array<string>} names The names of the artifacts to delete.
   * @return {angular.$q.Promise} A promise indicating success or failure.
   * @export
   */
  openDeleteArtifacts(names) {
    var directive = DeleteArtifactsDialogDirective;
    return this.grrDialogService_.openDirectiveDialog(
        directive.directive_name, {names: names});
  }

  /**
   * Shows an upload artifact dialog.
   *
   * @return {angular.$q.Promise} A promise indicating success or failure.
   * @export
   */
  openUploadArtifact() {
    var directive = UploadArtifactDialogDirective;
    return this.grrDialogService_.openDirectiveDialog(directive.directive_name);
  }
};

var ArtifactDialogService = exports.ArtifactDialogService;


/**
 * Name of the service in Angular.
 */
ArtifactDialogService.service_name = 'grrArtifactDialogService';
