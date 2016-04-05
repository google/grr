'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileTableDirective.FileTableController');
goog.provide('grrUi.client.virtualFileSystem.fileTableDirective.FileTableDirective');
goog.require('grrUi.client.virtualFileSystem.events');

goog.scope(function() {

var REFRESH_FOLDER_EVENT =
    grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT;

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

  /** @type {string} */
  this.filter;

  /**
   * This variable is set to a function by the infinite-table-directive
   * and can be used to force data reload from the server.
   *
   * @export {function()}
   */
  this.triggerUpdate;

  this.scope_.$watchGroup(['clientId', 'selectedFolderPath'],
      this.onDirectiveArgumentsChange_.bind(this));

  this.scope_.$on(REFRESH_FOLDER_EVENT,
      this.onFolderRefreshEvent_.bind(this));
};

var FileTableController =
    grrUi.client.virtualFileSystem.fileTableDirective.FileTableController;


/**
 * Is triggered whenever the client id or the selected folder path changes.
 *
 * @private
 */
FileTableController.prototype.onDirectiveArgumentsChange_ = function() {
  var selectedFolderPath = this.scope_['selectedFolderPath'];
  var clientId = this.scope_['clientId'];

  this.filter = '';
  this.fileListUrl = 'clients/' + clientId + '/vfs-index/' + selectedFolderPath;

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
 * Is triggered whenever an breadcrumb item was selected.
 *
 * @param {string} path
 * @export
 */
FileTableController.prototype.onBreadCrumbSelected = function(path) {
  this.scope_['selectedFolderPath'] = path;
  this.scope_['selectedFilePath'] = path;
};

/**
 * Selects a file by raising a FILE_SELECTION_CHANGED event.
 *
 * @param {Object} file
 * @export
 */
FileTableController.prototype.selectFile = function(file) {
  this.scope_['selectedFilePath'] = file['value']['path']['value'];
};

/**
 * Selects a folder by raising a FOLDER_SELECTION_CHANGED event.
 *
 * @param {Object} file
 * @export
 */
FileTableController.prototype.selectFolder = function(file) {
  if (file && file['value']['is_directory']['value']) {
    this.scope_['selectedFolderPath'] = file['value']['path']['value'];
  }
};

/**
 * Refreshes the current directory.
 *
 * @export
 */
FileTableController.prototype.refreshDirectory = function() {
  var clientId = this.scope_['clientId'];
  var selectedFolderPath = this.scope_['selectedFolderPath'];
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
  var clientId = this.scope_['clientId'];
  var selectedFolderPath = this.scope_['selectedFolderPath'];
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
  this.triggerUpdate();
};


/**
 * FileTableDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileTableDirective.FileTableDirective = function() {
  return {
    restrict: 'E',
    scope: {
      clientId: '=',
      selectedFolderPath: '=',
      selectedFilePath: '='
    },
    templateUrl: '/static/angular-components/client/virtual-file-system/file-table.html',
    controller: FileTableController,
    controllerAs: 'controller'
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
