'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileTableDirective.FileTableController');
goog.provide('grrUi.client.virtualFileSystem.fileTableDirective.FileTableDirective');
goog.require('grrUi.client.virtualFileSystem.events');
goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');

goog.scope(function() {

var REFRESH_FOLDER_EVENT =
    grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT;

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

  /** @type {boolean} */
  this.showFileList = true;

  /** @type {string} */
  this.fileListUrl;

  /** @type {?string} */
  this.refreshOperationId;

  /** @private {!angular.$q.Promise} */
  this.refreshOperationInterval_;

  /** @private {string} */
  this.lastSelectedFolderPath_;

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

  this.scope_.$on(REFRESH_FOLDER_EVENT,
      this.onFolderRefreshEvent_.bind(this));

  this.scope_.$watchGroup(['controller.fileContext.clientId',
                           'controller.fileContext.selectedFolderPath'],
      this.onContextChange_.bind(this));
};

var FileTableController =
    grrUi.client.virtualFileSystem.fileTableDirective.FileTableController;


/**
 * Is triggered whenever the client id or the selected folder path changes.
 *
 * @private
 */
FileTableController.prototype.onContextChange_ = function() {
  var clientId = this.fileContext['clientId'];
  var selectedFolderPath = this.fileContext['selectedFolderPath'];

  this.filter = '';
  this.fileListUrl = 'clients/' + clientId + '/vfs-index/' + selectedFolderPath;

  if (!this.showFileList && this.lastSelectedFolderPath_ !== selectedFolderPath) {
    this.showFileList = true;
  }
  this.lastSelectedFolderPath_ = selectedFolderPath;

  // Required to trigger an update even if the selectedFolderPath changes to the same value.
  if (this.triggerUpdate) {
    this.triggerUpdate();
  }
};

/**
 * Is triggered whenever the selected folder needs refreshing.
 *
 * @private
 */
FileTableController.prototype.onFolderRefreshEvent_ = function() {
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
  this.fileContext.selectFile(file['value']['path']['value']);
};

/**
 * Selects a folder by setting it as selected in the context.
 *
 * @param {Object} file
 * @export
 */
FileTableController.prototype.selectFolder = function(file) {
  if (file && file['value']['is_directory']['value']) {
    this.fileContext.selectFolder(file['value']['path']['value']);
  }
};

/**
 * Refreshes the current directory.
 *
 * @export
 */
FileTableController.prototype.refreshDirectory = function() {
  var clientId = this.fileContext['clientId'];
  var selectedFolderPath = this.fileContext['selectedFolderPath'];
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
  var selectedFolderPath = this.fileContext['selectedFolderPath'];
  var url = 'clients/' + clientId + '/vfs-refresh-operations/' + this.refreshOperationId;

  this.grrApiService_.get(url).then(
    function success(response) {
      if (response['data']['state'] === 'FINISHED') {
        this.refreshOperationId = '';
        this.interval_.cancel(this.refreshOperationInterval_);

        // Force directives to refresh the current folder.
        this.rootScope_.$broadcast(REFRESH_FOLDER_EVENT, selectedFolderPath);
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
    scope: {},
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
