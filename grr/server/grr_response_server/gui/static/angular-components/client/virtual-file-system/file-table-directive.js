goog.module('grrUi.client.virtualFileSystem.fileTableDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const fileContextDirective = goog.requireType('grrUi.client.virtualFileSystem.fileContextDirective');
const {REFRESH_FILE_EVENT, REFRESH_FOLDER_EVENT} = goog.require('grrUi.client.virtualFileSystem.events');
const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');
const {ensurePathIsFolder, getFolderFromPath} = goog.require('grrUi.client.virtualFileSystem.utils');


/** @const */
var ERROR_EVENT_NAME = ServerErrorButtonDirective.error_event_name;

/** @const */
var OPERATION_POLL_INTERVAL_MS = 1000;


/**
 * Controller for FileTableDirective.
 * @unrestricted
 */
const FileTableController = class {
  /**
   * @param {!angular.Scope} $rootScope
   * @param {!angular.Scope} $scope
   * @param {!angular.$interval} $interval
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($rootScope, $scope, $interval, grrApiService) {
    /** @private {!angular.Scope} */
    this.rootScope_ = $rootScope;

    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.$interval} */
    this.interval_ = $interval;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {string} */
    this.selectedFilePath_;

    /** @type {string} */
    this.fileListUrl;

    /** @type {?string} */
    this.lastRefreshOperationId;

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

    /**
     * @type {!fileContextDirective.FileContextController}
     */
    this.fileContext;

    /**
     * This variable is set to a function by the infinite-table-directive
     * and can be used to force data reload from the server.
     *
     * @export {function()}
     */
    this.triggerUpdate;

    /** @type {string} */
    this.viewMode = 'list';

    // We have to change 'viewMode' in the template via a ng-model binding.
    // Doing so requires having viewMode as a controller attribute (see
    // https://github.com/angular/angular.js/wiki/Understanding-Scopes).
    this.scope_.$watch('viewMode', newVal => this.viewMode = newVal);
    this.scope_.$watch(
        'controller.viewMode', newVal => this.scope_['viewMode'] = newVal);

    this.scope_.$on(REFRESH_FOLDER_EVENT, this.refreshFileList_.bind(this));
    this.scope_.$on(REFRESH_FILE_EVENT, this.refreshFileList_.bind(this));

    this.scope_.$watch(
        'controller.fileContext.clientId', this.refreshFileList_.bind(this));
    this.scope_.$watch(
        'controller.fileContext.selectedFilePath',
        this.onFilePathChange_.bind(this));
  }

  /**
   * @param {?string} newValue
   * @param {?string} oldValue
   *
   * @private
   */
  onFilePathChange_(newValue, oldValue) {
    var newFolder = getFolderFromPath(newValue);
    var oldFolder = getFolderFromPath(oldValue);

    if (newFolder !== oldFolder) {
      this.refreshFileList_();

      // Reset the "refresh directory" button state.
      this.lastRefreshOperationId = null;
    }
  }

  /**
   * Is triggered whenever the client id or the selected folder path changes.
   *
   * @private
   */
  refreshFileList_() {
    var clientId = this.fileContext['clientId'];
    var selectedFilePath = this.fileContext['selectedFilePath'] || '';
    var selectedFolderPath = getFolderFromPath(selectedFilePath);

    this.filter = '';
    this.fileListUrl =
        'clients/' + clientId + '/vfs-index/' + selectedFolderPath;

    // Required to trigger an update even if the selectedFolderPath changes to
    // the same value.
    if (this.triggerUpdate) {
      this.triggerUpdate();
    }
  }

  /**
   * Selects a file by setting it as selected in the context.
   *
   * @param {Object} file
   * @export
   */
  selectFile(file) {
    // Always reset the version when the file is selected.
    this.fileContext.selectFile(file['value']['path']['value'], 0);
  }

  /**
   * Selects a folder by setting it as selected in the context.
   *
   * @param {Object} file
   * @export
   */
  selectFolder(file) {
    var clientId = this.fileContext['clientId'];
    var filePath = file['value']['path']['value'];
    filePath = ensurePathIsFolder(filePath);

    // Always reset the version if the file is selected.
    this.fileContext.selectFile(filePath, 0);
    this.fileListUrl = 'clients/' + clientId + '/vfs-index/' + filePath;
  }

  /**
   * Refreshes the current directory.
   *
   * @export
   */
  startVfsRefreshOperation() {
    var clientId = this.fileContext['clientId'];
    var selectedFilePath = this.fileContext['selectedFilePath'];
    var selectedFolderPath = getFolderFromPath(selectedFilePath);

    var url = 'clients/' + clientId + '/vfs-refresh-operations';
    var refreshOperation = {
      file_path: selectedFolderPath,
      max_depth: 1,
      notify_user: false
    };

    // Setting this.lastRefreshOperationId means that the update button
    // will get disabled immediately.
    var operationId = this.lastRefreshOperationId = 'unknown';
    this.grrApiService_.post(url, refreshOperation)
        .then(function success(response) {
          operationId = this.lastRefreshOperationId =
              response['data']['operation_id'];

          var pollPromise = this.grrApiService_.poll(
              url + '/' + operationId, OPERATION_POLL_INTERVAL_MS);
          this.scope_.$on('$destroy', function() {
            this.grrApiService_.cancelPoll(pollPromise);
          }.bind(this));

          return pollPromise;
        }.bind(this))
        .then(function success() {
          this.rootScope_.$broadcast(
              REFRESH_FOLDER_EVENT, ensurePathIsFolder(selectedFolderPath));
        }.bind(this))
        .finally(function() {
          if (this.lastRefreshOperationId == operationId) {
            this.lastRefreshOperationId = null;
          }
        }.bind(this));
  }

  /**
   * Updates the file filter.
   *
   * @export
   */
  updateFilter() {
    this.filterValue = this.filterEditedValue;
  }

  /**
   * Downloads the timeline for the current directory.
   *
   * @param {string} format to use ('GRR' or 'BODY').
   * @export
   */
  downloadTimeline(format) {
    var clientId = this.fileContext['clientId'];
    var selectedFilePath = this.fileContext['selectedFilePath'] || '';
    var selectedFolderPath = getFolderFromPath(selectedFilePath);

    var url = 'clients/' + clientId + '/vfs-timeline-csv/' + selectedFolderPath;
    this.grrApiService_.downloadFile(url, {'format': format})
        .then(
            function success() {}.bind(this),
            function failure(response) {
              if (angular.isUndefined(response.status)) {
                this.rootScope_.$broadcast(
                    ERROR_EVENT_NAME,
                    {message: 'Couldn\'t export the timeline.'});
              }
            }.bind(this));
  }
};



/**
 * FileTableDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.FileTableDirective = function() {
  return {
    restrict: 'E',
    scope: {viewMode: '='},
    require: '^grrFileContext',
    templateUrl:
        '/static/angular-components/client/virtual-file-system/file-table.html',
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
exports.FileTableDirective.directive_name = 'grrFileTable';
