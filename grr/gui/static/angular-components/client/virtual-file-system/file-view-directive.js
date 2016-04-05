'use strict';

goog.provide('grrUi.client.virtualFileSystem.events');
goog.provide('grrUi.client.virtualFileSystem.fileViewDirective.FileViewController');
goog.provide('grrUi.client.virtualFileSystem.fileViewDirective.FileViewDirective');
goog.provide('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');
goog.provide('grrUi.client.virtualFileSystem.fileViewDirective.getFilePath');

goog.scope(function() {


var REFRESH_FOLDER_EVENT = "RefreshFolderEvent";
grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT = REFRESH_FOLDER_EVENT;


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
 * Converts given fileId to a filePath.
 *
 * @param {string} fileId The id to a file.
 * @return {string} The path of the file derived from the id.
 * @export
 */
module.getFilePath = function(fileId){
  var components = fileId.substring(1).split('-');
  var result = components.map(module.replaceEscapedChars_);
  return result.join('/');
};

/**
 * Replaces the escaped chars with their string value.
 * @param {string} item
 * @return {string} A string having all escaped chars replaced by their original meaning.
 * @private
 */
module.replaceEscapedChars_ = function(item){
  return item.replace(/_[0-9A-Z]{2}/g, function(escChar){
    var charCode = parseInt(escChar.substring(1), 16);
    return String.fromCharCode(charCode);
  });
};


/**
 * Controller for FileViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileViewDirective.FileViewController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.selectedFolderPath;

  /** @type {string} */
  this.selectedFilePath;

  /** @type {string} */
  this.clientId;

  if (grr.hash.t) {
    var folderPath = module.getFilePath(grr.hash.t);
    this.selectedFolderPath = folderPath;
  }

  this.scope_.$watch('clientId', this.onClientIdChange_.bind(this));
  this.scope_.$watch(function(){
    return this.selectedFolderPath;
  }.bind(this), this.onSelectedFolderPathChange_.bind(this));
};

var FileViewController =
    grrUi.client.virtualFileSystem.fileViewDirective.FileViewController;


/**
 * Handles changes of clientId binding.
 *
 * @private
 */
FileViewController.prototype.onClientIdChange_ = function() {
  var clientId = this.scope_['clientId'];

  if (angular.isDefined(clientId)) {
    if (clientId.indexOf('aff4') === 0) {
      this.clientId = clientId.split('/')[1];
    } else {
      this.clientId = clientId;
    }
  }
};

/**
 * Updates the URL hash to reflect changes in the folder selection.
 * @private
 */
FileViewController.prototype.onSelectedFolderPathChange_ = function() {
  if (this.selectedFolderPath) {
    var folderId = module.getFileId(this.selectedFolderPath);
    grr.publish('hash_state', 't', folderId);
  }
};


/**
 * FileViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileViewDirective.FileViewDirective = function() {
  return {
    restrict: 'E',
    scope: {
      clientId: '=',
    },
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
