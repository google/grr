'use strict';

goog.provide('grrUi.client.virtualFileSystem.events');
goog.provide('grrUi.client.virtualFileSystem.fileViewDirective.FileViewController');
goog.provide('grrUi.client.virtualFileSystem.fileViewDirective.FileViewDirective');
goog.provide('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');
goog.provide('grrUi.client.virtualFileSystem.fileViewDirective.getFilePath');

goog.scope(function() {


var REFRESH_FOLDER_EVENT = "RefreshFolderEvent";
grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT = REFRESH_FOLDER_EVENT;

var REFRESH_FILE_EVENT = "RefreshFileEvent";
grrUi.client.virtualFileSystem.events.REFRESH_FILE_EVENT = REFRESH_FILE_EVENT;


var module = grrUi.client.virtualFileSystem.fileViewDirective;

/**
 * Converts given filePath to a fileId.
 * @param {string} filePath The path to a file.
 * @return {string} A unique id for the file derived from the path.
 * @export
 */
module.getFileId = function(filePath){
  var components = filePath.split('/');
  var result = components.map(module.replaceInvalidChars_);
  return '_' + result.join('-');
};

/**
 * Replaces all non-alphanumeric characters with their hex representation.
 * @param {string} item
 * @return {string} A string with invalid chars replaced by their hex charcode value.
 * @private
 */
module.replaceInvalidChars_ = function(item){
  return item.replace(/[^a-zA-Z0-9]/g, function(invChar){
    var hex = invChar.charCodeAt(0).toString(16);
    return '_' + hex.toUpperCase();
  });
};


/**
 * Controller for FileViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileViewDirective.FileViewController = function(
    $scope, grrApiService, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.selectedFolderPath;

  /** @type {string} */
  this.selectedFilePath;

  /** @type {number} */
  this.fileVersion;

  /** @type {string} */
  this.clientId;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientIdChange_.bind(this));

  this.scope_.$watch('controller.selectedFolderPath',
      this.onSelectedFolderPathChange_.bind(this));
};

var FileViewController =
    grrUi.client.virtualFileSystem.fileViewDirective.FileViewController;


/**
 * Handles changes of the state params.
 *
 * @param {string} clientId The new value for the client id.
 * @private
 */
FileViewController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
};

/**
 * Updates the URL hash to reflect changes in the folder selection.
 * @private
 */
FileViewController.prototype.onSelectedFolderPathChange_ = function() {
  if (this.selectedFolderPath) {
    var folderId = module.getFileId(this.selectedFolderPath);
    this.grrRoutingService_.go('client.vfs', {folder: folderId});
  }
};


/**
 * FileViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileViewDirective.FileViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    templateUrl: '/static/angular-components/client/virtual-file-system/file-view.html',
    controller: FileViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileViewDirective.FileViewDirective.directive_name =
    'grrFileView';

});  // goog.scope
