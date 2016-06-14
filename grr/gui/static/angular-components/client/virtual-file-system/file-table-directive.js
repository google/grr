'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileTableDirective.FileTableController');
goog.provide('grrUi.client.virtualFileSystem.fileTableDirective.FileTableDirective');

goog.require('grrUi.client.virtualFileSystem.events');
goog.require('grrUi.client.virtualFileSystem.utils.ensurePathIsFolder');
goog.require('grrUi.client.virtualFileSystem.utils.getFolderFromPath');

goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');


goog.scope(function() {

var REFRESH_FOLDER_EVENT =
    grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT;

var REFRESH_FILE_EVENT =
    grrUi.client.virtualFileSystem.events.REFRESH_FILE_EVENT;

var ERROR_EVENT_NAME =
    grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.error_event_name;

var OPERATION_POLL_INTERVAL = 1000;


/**
 * Controller for FileTableDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileTableDirective.FileTableController = function(
    $rootScope, $scope, $interval, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.fileListUrl;

  /** @type {?string} */
  this.refreshOperationId;

  /** @private {!angular.$q.Promise} */
  this.refreshOperationInterval_;

  /** @private {string} */
  this.selectedFilePath_;

  /**
   * Used for UI binding with a filter edit field.
   * @export {string}
   */
  this.filterEditedValue = '';

  /**
   * Currently used filter value.
   * @export {string}
   */
  this.filterValue = '';

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  /**
   * This variable is set to a function by the infinite-table-directive
   * and can be used to force data reload from the server.
   *
   * @export {function()}
   */
  this.triggerUpdate;

  this.scope_.$on(REFRESH_FOLDER_EVENT, this.refreshFileList_.bind(this));
  this.scope_.$on(REFRESH_FILE_EVENT, this.refreshFileList_.bind(this));

  this.scope_.$watch('controller.fileContext.clientId', this.refreshFileList_.bind(this));
  this.scope_.$watch('controller.fileContext.selectedFilePath', this.onFilePathChange_.bind(this));
};

var FileTableController =
    grrUi.client.virtualFileSystem.fileTableDirective.FileTableController;


FileTableController.prototype.setViewMode = function(mode) {
  this.scope_['viewMode'] = mode;
};


FileTableController.prototype.onFilePathChange_ = function(newValue, oldValue) {
  var newFolder = grrUi.client.virtualFileSystem.utils.getFolderFromPath(newValue);
  var oldFolder = grrUi.client.virtualFileSystem.utils.getFolderFromPath(oldValue);

  if (newFolder !== oldFolder) {
    this.refreshFileList_();
  }
};

/**
 * Is triggered whenever the client id or the selected folder path changes.
 *
 * @private
 */
FileTableController.prototype.refreshFileList_ = function() {
  var clientId = this.fileContext['clientId'];
  var selectedFilePath = this.fileContext['selectedFilePath'] || '';
  var selectedFolderPath = grrUi.client.virtualFileSystem.utils.getFolderFromPath(
      selectedFilePath);

  this.filter = '';
  this.fileListUrl = 'clients/' + clientId + '/vfs-index/' + selectedFolderPath;

  // Required to trigger an update even if the selectedFolderPath changes to the same value.
  if (this.triggerUpdate) {
    this.triggerUpdate();
  }
};

/**
 * Selects a file by setting it as selected in the context.
 *
 * @param {Object} file
 * @export
 */
FileTableController.prototype.selectFile = function(file) {
  // Always reset the version when the file is selected.
  this.fileContext.selectFile(file['value']['path']['value'], 0);
};

/**
 * Selects a folder by setting it as selected in the context.
 *
 * @param {Object} file
 * @export
 */
FileTableController.prototype.selectFolder = function(file) {
  var clientId = this.fileContext['clientId'];
  var filePath = file['value']['path']['value'];
  filePath = grrUi.client.virtualFileSystem.utils.ensurePathIsFolder(filePath);

  // Always reset the version if the file is selected.
  this.fileContext.selectFile(filePath, 0);
  this.fileListUrl = 'clients/' + clientId + '/vfs-index/' + filePath;
};

/**
 * Refreshes the current directory.
 *
 * @export
 */
FileTableController.prototype.startVfsRefreshOperation = function() {
  var clientId = this.fileContext['clientId'];
  var selectedFilePath = this.fileContext['selectedFilePath'];
  var selectedFolderPath = grrUi.client.virtualFileSystem.utils.getFolderFromPath(
      selectedFilePath);
  var url = 'clients/' + clientId + '/vfs-refresh-operations';

  var refreshOperation = {
    file_path: selectedFolderPath,
    max_depth: 0,
    notify_user: false
  };

  this.grrApiService_.post(
      url, refreshOperation).then(
      function success(response) {
        this.refreshOperationId = response['data']['operation_id'];
        this.monitorRefreshOperation_();
      }.bind(this),
      function failure(response) {
        this.refreshOperationId = null;
        this.interval_.cancel(this.refreshOperationInterval_);
      }.bind(this));
};

/**
 * Polls the refresh operation state.
 *
 * @private
 */
FileTableController.prototype.monitorRefreshOperation_ = function() {
  this.refreshOperationInterval_ = this.interval_(
      this.pollRefreshOperationState_.bind(this),
      OPERATION_POLL_INTERVAL);
};

/**
 * Polls the refresh operation state.
 *
 * @private
 */
FileTableController.prototype.pollRefreshOperationState_ = function() {
  var clientId = this.fileContext['clientId'];
  var url = 'clients/' + clientId + '/vfs-refresh-operations/' + this.refreshOperationId;

  this.grrApiService_.get(url).then(
    function success(response) {
      if (response['data']['state'] === 'FINISHED') {
        this.refreshOperationId = '';
        this.interval_.cancel(this.refreshOperationInterval_);

        // Force directives to refresh the current folder.
        this.rootScope_.$broadcast(REFRESH_FOLDER_EVENT);
      }
    }.bind(this),
    function failure(response) {
      this.refreshOperationId = null;
      this.interval_.cancel(this.refreshOperationInterval_);
    }.bind(this));
};

/**
 * Updates the file filter.
 *
 * @export
 */
FileTableController.prototype.updateFilter = function() {
  this.filterValue = this.filterEditedValue;
};

/**
 * Downloads the timeline for the current directory.
 *
 * @export
 */
FileTableController.prototype.downloadTimeline = function() {
  var clientId = this.fileContext['clientId'];
  var selectedFolderPath = this.fileContext['selectedFolderPath'];

  var url = 'clients/' + clientId + '/vfs-timeline-csv/' + selectedFolderPath;
  this.grrApiService_.downloadFile(url).then(
      function success() {}.bind(this),
      function failure(response) {
        if (angular.isUndefined(response.status)) {
          this.rootScope_.$broadcast(
              ERROR_EVENT_NAME, {
                message: 'Couldn\'t export the timeline.'
              });
        }
      }.bind(this)
  );
};


/**
 * FileTableDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileTableDirective.FileTableDirective = function() {
  return {
    restrict: 'E',
    scope: {
      viewMode: '='
    },
    require: '^grrFileContext',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-table.html',
    controller: FileTableController,
    controllerAs: 'controller',
    link: function(scope, element, attrs, fileContextController) {
      scope.controller.fileContext = fileContextController;
    }
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileTableDirective.FileTableDirective.directive_name =
    'grrFileTable';

});  // goog.scope
