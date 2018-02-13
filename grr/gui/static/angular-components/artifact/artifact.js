'use strict';

goog.provide('grrUi.artifact.artifact');
goog.provide('grrUi.artifact.artifact.artifactModule');

goog.require('grrUi.artifact.artifactDescriptorDirective');  // USE: ArtifactDescriptorDirective
goog.require('grrUi.artifact.artifactDescriptorsService');  // USE: ArtifactDescriptorsService
goog.require('grrUi.artifact.artifactDialogService');  // USE: ArtifactDialogService
goog.require('grrUi.artifact.artifactManagerViewDirective');  // USE: ArtifactManagerViewDirective
goog.require('grrUi.artifact.artifactNameDirective');  // USE: ArtifactNameDirective
goog.require('grrUi.artifact.artifactsListFormDirective');  // USE: ArtifactsListFormDirective
goog.require('grrUi.artifact.deleteArtifactsDialogDirective');  // USE: DeleteArtifactsDialogDirective
goog.require('grrUi.artifact.uploadArtifactDialogDirective');  // USE: UploadArtifactDialogDirective

goog.require('grrUi.core.core');          // USE: coreModule
goog.require('grrUi.forms.forms');        // USE: formsModule
goog.require('grrUi.semantic.semantic');  // USE: semanticModule


/**
 * Module with artifact-related directives.
 */
grrUi.artifact.artifact.artifactModule = angular.module('grrUi.artifact', [
  grrUi.core.core.coreModule.name, grrUi.forms.forms.formsModule.name,
  grrUi.semantic.semantic.semanticModule.name, 'ui.bootstrap'
]);

grrUi.artifact.artifact.artifactModule.directive(
    grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective
        .directive_name,
    grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective);
grrUi.artifact.artifact.artifactModule.directive(
    grrUi.artifact.artifactNameDirective.ArtifactNameDirective.directive_name,
    grrUi.artifact.artifactNameDirective.ArtifactNameDirective);
grrUi.artifact.artifact.artifactModule.directive(
    grrUi.artifact.artifactManagerViewDirective.ArtifactManagerViewDirective
        .directive_name,
    grrUi.artifact.artifactManagerViewDirective.ArtifactManagerViewDirective);
grrUi.artifact.artifact.artifactModule.directive(
    grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective
        .directive_name,
    grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective);
grrUi.artifact.artifact.artifactModule.directive(
    grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective
        .directive_name,
    grrUi.artifact.deleteArtifactsDialogDirective
        .DeleteArtifactsDialogDirective);
grrUi.artifact.artifact.artifactModule.directive(
    grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective
        .directive_name,
    grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective);

grrUi.artifact.artifact.artifactModule.service(
    grrUi.artifact.artifactDescriptorsService.ArtifactDescriptorsService
        .service_name,
    grrUi.artifact.artifactDescriptorsService.ArtifactDescriptorsService);
grrUi.artifact.artifact.artifactModule.service(
    grrUi.artifact.artifactDialogService.ArtifactDialogService.service_name,
    grrUi.artifact.artifactDialogService.ArtifactDialogService);

grrUi.artifact.artifact.artifactModule.run(function(
    grrSemanticRepeatedFormDirectivesRegistryService) {
  var registry = grrSemanticRepeatedFormDirectivesRegistryService;

  registry.registerDirective(
      grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective
          .semantic_type,
      grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective);
});


grrUi.artifact.artifact.artifactModule.run(function(
    grrSemanticValueDirectivesRegistryService) {
  var registry = grrSemanticValueDirectivesRegistryService;

  registry.registerDirective(
      grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective
          .semantic_type,
      grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective);
  registry.registerDirective(
      grrUi.artifact.artifactNameDirective.ArtifactNameDirective
          .semantic_type,
      grrUi.artifact.artifactNameDirective.ArtifactNameDirective);
});
