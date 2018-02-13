'use strict';

goog.module('grrUi.artifact.artifact');
goog.module.declareLegacyNamespace();

const {ArtifactDescriptorDirective} = goog.require('grrUi.artifact.artifactDescriptorDirective');
const {ArtifactDescriptorsService} = goog.require('grrUi.artifact.artifactDescriptorsService');
const {ArtifactDialogService} = goog.require('grrUi.artifact.artifactDialogService');
const {ArtifactManagerViewDirective} = goog.require('grrUi.artifact.artifactManagerViewDirective');
const {ArtifactNameDirective} = goog.require('grrUi.artifact.artifactNameDirective');
const {ArtifactsListFormDirective} = goog.require('grrUi.artifact.artifactsListFormDirective');
const {DeleteArtifactsDialogDirective} = goog.require('grrUi.artifact.deleteArtifactsDialogDirective');
const {UploadArtifactDialogDirective} = goog.require('grrUi.artifact.uploadArtifactDialogDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {formsModule} = goog.require('grrUi.forms.forms');
const {semanticModule} = goog.require('grrUi.semantic.semantic');



/**
 * Module with artifact-related directives.
 */
exports.artifactModule = angular.module(
    'grrUi.artifact',
    [coreModule.name, formsModule.name, semanticModule.name, 'ui.bootstrap']);

exports.artifactModule.directive(
    ArtifactDescriptorDirective.directive_name, ArtifactDescriptorDirective);
exports.artifactModule.directive(
    ArtifactNameDirective.directive_name, ArtifactNameDirective);
exports.artifactModule.directive(
    ArtifactManagerViewDirective.directive_name, ArtifactManagerViewDirective);
exports.artifactModule.directive(
    ArtifactsListFormDirective.directive_name, ArtifactsListFormDirective);
exports.artifactModule.directive(
    DeleteArtifactsDialogDirective.directive_name,
    DeleteArtifactsDialogDirective);
exports.artifactModule.directive(
    UploadArtifactDialogDirective.directive_name,
    UploadArtifactDialogDirective);

exports.artifactModule.service(
    ArtifactDescriptorsService.service_name, ArtifactDescriptorsService);
exports.artifactModule.service(
    ArtifactDialogService.service_name, ArtifactDialogService);

exports.artifactModule.run(function(
    grrSemanticRepeatedFormDirectivesRegistryService) {
  var registry = grrSemanticRepeatedFormDirectivesRegistryService;

  registry.registerDirective(
      ArtifactsListFormDirective.semantic_type, ArtifactsListFormDirective);
});


exports.artifactModule.run(function(grrSemanticValueDirectivesRegistryService) {
  var registry = grrSemanticValueDirectivesRegistryService;

  registry.registerDirective(
      ArtifactDescriptorDirective.semantic_type, ArtifactDescriptorDirective);
  registry.registerDirective(
      ArtifactNameDirective.semantic_type, ArtifactNameDirective);
});
