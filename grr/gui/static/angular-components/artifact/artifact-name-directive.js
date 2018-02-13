'use strict';

goog.module('grrUi.artifact.artifactNameDirective');
goog.module.declareLegacyNamespace();



/** @const {string} */
var SYSTEM_ARTIFACT_TYPE = 'SYSTEM';

/** @const {string} */
var USER_ARTIFACT_TYPE = 'USER';

/** @const {string} */
var UNKNOWN_ARTIFACT_TYPE = 'UNKNOWN';


/**
 * Controller for ArtifactNameDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.artifact.artifactDescriptorsService.ArtifactDescriptorsService}
 *     grrArtifactDescriptorsService
 * @constructor
 * @ngInject
 */
const ArtifactNameController = function(
    $scope, grrArtifactDescriptorsService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.artifact.artifactDescriptorsService.ArtifactDescriptorsService} */
  this.grrArtifactDescriptorsService_ = grrArtifactDescriptorsService;

  /** @type {string} */
  this.artifactType;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};




/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newArtifactName New ArtifactName RDFValue.
 * @private
 */
ArtifactNameController.prototype.onValueChange_ = function(newArtifactName) {
  if (!angular.isObject(newArtifactName)) {
    return;
  }

  this.grrArtifactDescriptorsService_.getDescriptorByName(
      newArtifactName['value']).then(
          function(descriptor) {
            if (angular.isDefined(descriptor)) {
              var isCustom = descriptor['value']['is_custom']['value'];
              this.artifactType =
                  isCustom ? USER_ARTIFACT_TYPE : SYSTEM_ARTIFACT_TYPE;
            } else {
              this.artifactType = UNKNOWN_ARTIFACT_TYPE;
            }
          }.bind(this));
};

/**
 * Directive that displays ArtifactName values.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ArtifactNameDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/artifact/artifact-name.html',
    controller: ArtifactNameController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.ArtifactNameDirective.directive_name = 'grrArtifactName';

/**
 * Artifact type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.ArtifactNameDirective.semantic_type = 'ArtifactName';
