'use strict';

goog.provide('grrUi.artifact.module');


goog.require('grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective');
goog.require('grrUi.artifact.artifactDialogService.ArtifactDialogService');
goog.require('grrUi.artifact.artifactManagerViewDirective.ArtifactManagerViewDirective');
goog.require('grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective');
goog.require('grrUi.artifact.deleteArtifactsDialogDirective.DeleteArtifactsDialogDirective');
goog.require('grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective');

goog.require('grrUi.core.module');
goog.require('grrUi.forms.module');
goog.require('grrUi.semantic.module');


/**
 * Module with artifact-related directives.
 */
grrUi.artifact.module = angular.module('grrUi.artifact',
                                       [grrUi.core.module.name,
                                        grrUi.forms.module.name,
                                        grrUi.semantic.module.name,
                                        'ui.bootstrap']);

grrUi.artifact.module.directive(
    grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective
        .directive_name,
    grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective);
grrUi.artifact.module.directive(
    grrUi.artifact.artifactManagerViewDirective.ArtifactManagerViewDirective
        .directive_name,
    grrUi.artifact.artifactManagerViewDirective.ArtifactManagerViewDirective);
grrUi.artifact.module.directive(
    grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective
        .directive_name,
    grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective);
grrUi.artifact.module.directive(
    grrUi.artifact.deleteArtifactsDialogDirective
        .DeleteArtifactsDialogDirective.directive_name,
    grrUi.artifact.deleteArtifactsDialogDirective
        .DeleteArtifactsDialogDirective);
grrUi.artifact.module.directive(
    grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective
        .directive_name,
    grrUi.artifact.uploadArtifactDialogDirective.UploadArtifactDialogDirective);

grrUi.core.module.service(
    grrUi.artifact.artifactDialogService.ArtifactDialogService.service_name,
    grrUi.artifact.artifactDialogService.ArtifactDialogService);

grrUi.artifact.module.run(
    function(grrSemanticRepeatedFormDirectivesRegistryService) {
  var registry = grrSemanticRepeatedFormDirectivesRegistryService;

  registry.registerDirective(
      grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective
          .semantic_type,
      grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective);
});


grrUi.artifact.module.run(function(grrSemanticValueDirectivesRegistryService) {
  var registry = grrSemanticValueDirectivesRegistryService;

  registry.registerDirective(
      grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective
          .semantic_type,
      grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective);
});
