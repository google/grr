'use strict';

goog.provide('grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorController');
goog.provide('grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective');


goog.scope(function() {


/**
 * Controller for ArtifactDescriptorDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;
};

var ArtifactDescriptorController =
    grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorController;


/**
 * Directive that displays artifact descriptor (artifact itself, processors and
 * source).
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective = function() {
  return {
    scope: {
      value: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/artifact/artifact-descriptor.html',
    controller: ArtifactDescriptorController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective
    .directive_name = 'grrArtifactDescriptor';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.artifact.artifactDescriptorDirective.ArtifactDescriptorDirective
    .semantic_type = 'ArtifactDescriptor';


});  // goog.scope
