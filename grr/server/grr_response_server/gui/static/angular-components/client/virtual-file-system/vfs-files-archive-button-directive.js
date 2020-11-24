goog.module('grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');
const {getFolderFromPath} = goog.require('grrUi.client.virtualFileSystem.utils');


/** @const */
var ERROR_EVENT_NAME = ServerErrorButtonDirective.error_event_name;


/** @const {number} */
exports.DOWNLOAD_EVERYTHING_REENABLE_DELAY = 30000;

/** @const */
var DOWNLOAD_EVERYTHING_REENABLE_DELAY =
    exports.DOWNLOAD_EVERYTHING_REENABLE_DELAY;


/**
 * Controller for VfsFilesArchiveButtonDirective.
 * @unrestricted
 */
const VfsFilesArchiveButtonController = class {
  /**
   * @param {!angular.Scope} $rootScope
   * @param {!angular.Scope} $scope
   * @param {!angular.$timeout} $timeout
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($rootScope, $scope, $timeout, grrApiService) {
    /** @private {!angular.Scope} */
    this.rootScope_ = $rootScope;

    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.$timeout} */
    this.timeout_ = $timeout;

    /** @private {!apiService.ApiService} */
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
  }

  /**
   * Starts download of an archive corresponding to a given path. Empty string
   * means that archive of all the files will be downloaded.
   *
   * @param {string} path
   */
  _download(path) {
    var clientId = this.scope_['clientId'];
    var url = 'clients/' + clientId + '/vfs-files-archive/' + path;
    this.grrApiService_.downloadFile(url).then(
        function success() {}.bind(this),
        function failure(response) {
          if (angular.isUndefined(response.status)) {
            this.rootScope_.$broadcast(
                ERROR_EVENT_NAME,
                {message: 'Couldn\'t download the VFS archive.'});
          }
        }.bind(this));
  }

  /**
   * Handles mouse clicks on 'download current folder' dropdown menu item.
   *
   * @param {Event} e
   * @export
   */
  downloadCurrentFolder(e) {
    e.preventDefault();

    if (!this.downloadCurrentFolderDisabled) {
      var folderPath = getFolderFromPath(this.scope_['filePath']);
      this._download(folderPath);
      this.downloadCurrentFolderDisabled = true;
    }
  }

  /**
   * Handles mouse clicks on 'download everything' dropdown menu item.
   *
   * @param {Event} e
   * @export
   */
  downloadEverything(e) {
    e.preventDefault();

    if (!this.downloadEverythingDisabled) {
      this._download('');
      this.downloadEverythingDisabled = true;

      this.timeout_(function() {
        this.downloadEverythingDisabled = false;
      }.bind(this), DOWNLOAD_EVERYTHING_REENABLE_DELAY);
    }
  }
};



/**
 * VfsFilesArchiveButtonDirective renders a button that shows a dialog that
 * allows users to change their personal settings.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.VfsFilesArchiveButtonDirective = function() {
  return {
    scope: {clientId: '=', filePath: '='},
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
exports.VfsFilesArchiveButtonDirective.directive_name =
    'grrVfsFilesArchiveButton';
