'use strict';

goog.module('grrUi.artifact.artifactManagerViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for OutputPluginNoteDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.artifact.artifactDialogService.ArtifactDialogService} grrArtifactDialogService
 * @ngInject
 */
const ArtifactManagerViewController =
    function($scope, grrApiService, grrArtifactDialogService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

 /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.artifact.artifactDialogService.ArtifactDialogService} */
  this.grrArtifactDialogService_ = grrArtifactDialogService;

  /**
   * This variable is bound to grr-infinite-table's trigger-update attribute
   * and therefore is set by that directive to a function that triggers
   * table update.
   * @export {function()}
   */
  this.triggerUpdate;

  /** @export {Array.<Object>} */
  this.descriptors = [];

  /** @export {Object.<string, boolean>} */
  this.selectedDescriptors = {};

  /** @export {number} */
  this.numSelectedDescriptors = 0;

  /** @export {boolean} */
  this.allDescriptorsSelected = false;
};


/**
 * Artifacts list API url.
 * @const {string}
 */
ArtifactManagerViewController.prototype.artifactsUrl = '/artifacts';


/**
 * Transforms table items before they get shown.
 *
 * @param {!Array<Object>} items Items to be transformed.
 * @return {!Array<Object>} Transformed items.
 * @export
 * @suppress {missingProperties} For items, as they crom from JSON response.
 */
ArtifactManagerViewController.prototype.transformItems = function(items) {
  this.descriptors = [];

  angular.forEach(items, function(item) {
    if (item.value.is_custom.value) {
      this.descriptors.push(item);
    }
  }.bind(this));

  return this.descriptors;
};


/**
 * Selects all artifacts in the table
 *
 * @export
 */
ArtifactManagerViewController.prototype.selectAll = function() {
  angular.forEach(this.descriptors, function(descriptor) {
    this.selectedDescriptors[descriptor.value.artifact.value.name.value] =
        this.allDescriptorsSelected;
  }.bind(this));

  this.updateNumSelectedDescriptors();
};


/**
 * Shows "Upload artifact dialog.
 *
 * @export
 */
ArtifactManagerViewController.prototype.upload = function() {
  var result = this.grrArtifactDialogService_.openUploadArtifact();
  result.then(function resolve() {
    this.triggerUpdate();
  }.bind(this));
};


/**
 * Shows confirmation dialog and deletes selected artifacts.
 *
 * @export
 */
ArtifactManagerViewController.prototype.deleteSelected = function() {
  var namesToDelete = [];
  for (var name in this.selectedDescriptors) {
    if (this.selectedDescriptors[name]) {
      namesToDelete.push(name);
    }
  }

  var result = this.grrArtifactDialogService_.openDeleteArtifacts(namesToDelete);
  result.then(function resolve() {
    this.selectedDescriptors = {};
    this.numSelectedDescriptors = 0;
    this.triggerUpdate();
  }.bind(this));
};


/**
 * Updates number of selected descriptors by traversing selection dictionary.
 *
 * @export
 */
ArtifactManagerViewController.prototype.updateNumSelectedDescriptors =
    function() {
  var count = 0;
  for (var key in this.selectedDescriptors) {
    if (this.selectedDescriptors[key]) {
      ++count;
    }
  }

  this.numSelectedDescriptors = count;
};


/**
 * Directive that displays artifact manager view.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ArtifactManagerViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/artifact/' +
        'artifact-manager-view.html',
    controller: ArtifactManagerViewController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ArtifactManagerViewDirective.directive_name = 'grrArtifactManagerView';
