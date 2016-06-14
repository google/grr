'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileLegacyViewDirective.FileLegacyViewController');
goog.provide('grrUi.client.virtualFileSystem.fileLegacyViewDirective.FileLegacyViewDirective');

goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');
goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFilePathFromId');

goog.require('grrUi.client.virtualFileSystem.utils.ensurePathIsFolder');
goog.require('grrUi.client.virtualFileSystem.utils.getFolderFromPath');

goog.scope(function() {


var getFileId = grrUi.client.virtualFileSystem.fileViewDirective.getFileId;
var getFilePathFromId = grrUi.client.virtualFileSystem.fileViewDirective.getFilePathFromId;

var getFolderFromPath = grrUi.client.virtualFileSystem.utils.getFolderFromPath;
var ensurePathIsFolder = grrUi.client.virtualFileSystem.utils.ensurePathIsFolder;


/**
 * Controller for FileLegacyViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileLegacyViewDirective.FileLegacyViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.clientUrn;

  /** @type {string} */
  this.aff4Path;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, ['clientId', 'path', 'version'],
      this.onUrlRoutingParamsChanged_.bind(this));

  // Most jsTree instances are still rendered using the legacy GRR code. Until
  // all parts are migrated, the following event can be used to update URLs
  // based on tree selection. This code can be removed once the legacy VFS view
  // is deprecated.
  this.scope_.$on('grrTreeSelectionChanged', function(event, nodeId) {
    grr.hash.t = nodeId;
    var path = ensurePathIsFolder(getFilePathFromId(nodeId));
    this.grrRoutingService_.go('client.vfs', {path: path});
  }.bind(this));
};

var FileLegacyViewController =
    grrUi.client.virtualFileSystem.fileLegacyViewDirective.FileLegacyViewController;


/**
 * Handles changes to the client id state param.
 *
 * @param {string} newValues The new values of the watched state params.
 * @param {Object=} opt_stateParams The new values for all state params.
 * @private
 */
FileLegacyViewController.prototype.onUrlRoutingParamsChanged_ = function(newValues, opt_stateParams) {
  this.clientUrn = 'aff4:/' + opt_stateParams['clientId'];
  this.aff4Path = this.clientUrn; // Set default value for aff4Path.

  if (opt_stateParams['path']) {
    this.aff4Path += '/' + opt_stateParams['path'];
    grr.hash.t = getFileId(getFolderFromPath(opt_stateParams['path']));
  }
};

/**
 * FileLegacyViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileLegacyViewDirective.FileLegacyViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-legacy-view.html',
    controller: FileLegacyViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileLegacyViewDirective.FileLegacyViewDirective.directive_name =
    'grrFileLegacyView';

});  // goog.scope
