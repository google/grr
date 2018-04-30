'use strict';

goog.module('grrUi.artifact.artifactDescriptorDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ArtifactDescriptorDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
const ArtifactDescriptorController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;
};



/**
 * Directive that displays artifact descriptor (artifact itself, processors and
 * source).
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ArtifactDescriptorDirective = function() {
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
exports.ArtifactDescriptorDirective.directive_name = 'grrArtifactDescriptor';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.ArtifactDescriptorDirective.semantic_type = 'ArtifactDescriptor';
