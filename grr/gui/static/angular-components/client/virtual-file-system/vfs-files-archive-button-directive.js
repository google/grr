'use strict';

goog.provide('grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective.DOWNLOAD_EVERYTHING_REENABLE_DELAY');
goog.provide('grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective.VfsFilesArchiveButtonController');
goog.provide('grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective.VfsFilesArchiveButtonDirective');

goog.require('grrUi.client.virtualFileSystem.utils.ensurePathIsFolder');
goog.require('grrUi.client.virtualFileSystem.utils.getFolderFromPath');

goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');

goog.scope(function() {

var ERROR_EVENT_NAME =
    grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.error_event_name;

var ensurePathIsFolder = grrUi.client.virtualFileSystem.utils.ensurePathIsFolder;
var getFolderFromPath = grrUi.client.virtualFileSystem.utils.getFolderFromPath;


/** @const {number} */
grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective
    .DOWNLOAD_EVERYTHING_REENABLE_DELAY = 30000;

var DOWNLOAD_EVERYTHING_REENABLE_DELAY =
    grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective
    .DOWNLOAD_EVERYTHING_REENABLE_DELAY;


/**
 * Controller for VfsFilesArchiveButtonDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!angular.$timeout} $timeout
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective
    .VfsFilesArchiveButtonController = function(
        $rootScope, $scope, $timeout, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$timeout} */
  this.timeout_ = $timeout;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {boolean} */
  this.downloadEverythingDisabled = false;

  /** @type {boolean} */
  this.downloadCurrentFolderDisabled = false;

  this.scope_.$watch('clientId', function() {
    this.downloadEverythingDisabled = false;
  }.bind(this));

  this.scope_.$watch('filePath', function(value) {
    this.downloadCurrentFolderDisabled = false;
  }.bind(this));
};
var VfsFilesArchiveButtonController =
    grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective
    .VfsFilesArchiveButtonController;


/**
 * Starts download of an archive corresponding to a given path. Empty string
 * means that archive of all the files will be downloaded.
 *
 * @param {string} path
 */
VfsFilesArchiveButtonController.prototype._download = function(path) {
  var clientId = this.scope_['clientId'];
  var url = 'clients/' + clientId + '/vfs-files-archive/' + path;
  this.grrApiService_.downloadFile(url).then(
      function success() {}.bind(this),
      function failure(response) {
        if (angular.isUndefined(response.status)) {
          this.rootScope_.$broadcast(
              ERROR_EVENT_NAME, {
                message: 'Couldn\'t download the VFS archive.'
              });
        }
      }.bind(this)
  );
};

/**
 * Handles mouse clicks on 'download current folder' dropdown menu item.
 *
 * @param {Event} e
 * @export
 */
VfsFilesArchiveButtonController.prototype.downloadCurrentFolder = function(e) {
  e.preventDefault();

  if (!this.downloadCurrentFolderDisabled) {
    var folderPath = getFolderFromPath(this.scope_['filePath']);
    this._download(folderPath);
    this.downloadCurrentFolderDisabled = true;
  }
};

/**
 * Handles mouse clicks on 'download everything' dropdown menu item.
 *
 * @param {Event} e
 * @export
 */
VfsFilesArchiveButtonController.prototype.downloadEverything = function(e) {
  e.preventDefault();

  if (!this.downloadEverythingDisabled) {
    this._download('');
    this.downloadEverythingDisabled = true;

    this.timeout_(function() {
      this.downloadEverythingDisabled = false;
    }.bind(this), DOWNLOAD_EVERYTHING_REENABLE_DELAY);
  }
};


/**
 * VfsFilesArchiveButtonDirective renders a button that shows a dialog that allows
 * users to change their personal settings.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective
    .VfsFilesArchiveButtonDirective = function() {
  return {
    scope: {
      clientId: '=',
      filePath: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/client/virtual-file-system/' +
        'vfs-files-archive-button.html',
    controller: VfsFilesArchiveButtonController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective.VfsFilesArchiveButtonDirective
    .directive_name = 'grrVfsFilesArchiveButton';

});  // goog.scope
