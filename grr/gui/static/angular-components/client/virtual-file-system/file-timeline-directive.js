'use strict';

goog.module('grrUi.client.virtualFileSystem.fileTimelineDirective');
goog.module.declareLegacyNamespace();

const {REFRESH_FILE_EVENT, REFRESH_FOLDER_EVENT} = goog.require('grrUi.client.virtualFileSystem.events');
const {getFolderFromPath} = goog.require('grrUi.client.virtualFileSystem.utils');


/**
 * Controller for FileTimelineDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const FileTimelineController = function(
    $scope, $interval, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  /** @type {Array} */
  this.timelineItems;

  /** @type {Object} */
  this.selectedItem;

  /** @type {boolean} */
  this.inProgress;

  /** @type {string} */
  this.currentFolder;

  /**
   * This variable is set to a function by the infinite-table-directive
   * and can be used to force data reload from the server.
   *
   * @export {function()}
   */
  this.triggerUpdate;

  this.scope_.$on(REFRESH_FOLDER_EVENT, this.refreshTimeline_.bind(this));
  this.scope_.$on(REFRESH_FILE_EVENT, this.refreshTimeline_.bind(this));

  this.scope_.$watch('controller.fileContext.clientId', this.refreshTimeline_.bind(this));
  this.scope_.$watch('controller.fileContext.selectedFilePath', this.onFilePathChange_.bind(this));
};



/**
 * @param {?string} newFilePath
 *
 * @private
 */
FileTimelineController.prototype.onFilePathChange_ = function(newFilePath) {
  if (angular.isUndefined(newFilePath)) {
    return;
  }

  var newFolder = getFolderFromPath(newFilePath);

  // If a folder is selected (marked by the ending slash), we should always
  // refresh.
  if (newFilePath.endsWith('/') || angular.isUndefined(this.currentFolder)) {
    this.currentFolder = newFolder;
    this.refreshTimeline_();
    return;
  }

  var newFolderComponents = newFolder.split('/');
  var currentFolderComponents = this.currentFolder.split('/');
  for (var i = 0; i < currentFolderComponents.length; ++i) {
    if (newFolderComponents[i] != currentFolderComponents[i]) {
      this.refreshTimeline_();
      this.currentFolder = newFolder;
    }
  }
};

/**
 * Refreshes the current timeline view.
 *
 * @private
 */
FileTimelineController.prototype.refreshTimeline_ = function() {
  var clientId = this.fileContext['clientId'];
  var selectedFolderPath = getFolderFromPath(
      this.fileContext['selectedFilePath']);

  if (angular.isUndefined(this.currentFolder)) {
    this.currentFolder = selectedFolderPath;
  }

  this.inProgress = true;

  var url = 'clients/' + clientId + '/vfs-timeline/' + selectedFolderPath;
  this.grrApiService_.get(url).then(this.onTimelineFetched_.bind(this))
      .finally(function() {
        this.inProgress = false;
      }.bind(this));
};

/**
 * Processes timeline data received from the server.
 *
 * @param {Object} response Server response.
 * @private
 */
FileTimelineController.prototype.onTimelineFetched_ = function(response) {
  var selectedFilePath = this.fileContext['selectedFilePath'];
  var selectedFileVersion = this.fileContext['selectedFileVersion'];

  this.timelineItems = response.data['items'];

  // Make sure that the currently selected file (identified by
  // fileContext.selectedFilePath and fileContext.selectedFileVersion) is
  // selected after the list is updated.
  this.selectedItem = this.timelineItems.find(function(item) {
    var v = item['value'];
    if (v['file_path']['value'] === selectedFilePath) {
      return !selectedFileVersion ||
          v['timestamp']['value'] === selectedFileVersion;
    }
  }.bind(this)) || null;

  if (this.selectedItem && !selectedFileVersion) {
    // If the version wasn't set explicitly on the context, set it, so that the
    // URL gets updated.
    this.fileContext['selectedFileVersion'] =
        this.selectedItem['value']['timestamp']['value'];
  }

  if (this.triggerUpdate) {
    this.triggerUpdate();
  }
};

/**
 * Selects the file causing the timeline event.
 *
 * @param {Object} timelineItem
 * @export
 */
FileTimelineController.prototype.selectFile = function(timelineItem) {
  this.selectedItem = timelineItem;

  var clientId = this.fileContext['clientId'];
  var selectedFilePath = timelineItem['value']['file_path']['value'];
  var timestamp = timelineItem['value']['timestamp']['value'];

  var url = 'clients/' + clientId + '/vfs-version-times/' + selectedFilePath;
  this.grrApiService_.get(url).then(function success(response) {
    var versions = response.data['times'];

    // Find the closest available version in the future.
    var fileVersion = Number.MAX_VALUE;
    angular.forEach(versions, function(version) {
      if (version['value'] >= timestamp) {
        fileVersion = Math.min(fileVersion, version['value']);
      }
    });

    // If there is no version afterwards, select the newest one.
    if (fileVersion === Number.MAX_VALUE) {
      if (versions.length){
        fileVersion = versions[0]['value']; // Versions are sorted from newest to oldest.
      } else {
        fileVersion = null;
      }
    }

    this.fileContext.selectFile(selectedFilePath, fileVersion);
  }.bind(this));
};


/**
 * FileTimelineDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.FileTimelineDirective = function() {
  return {
    restrict: 'E',
    scope: {
      filterValue: '=?'
    },
    require: '^grrFileContext',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-timeline.html',
    controller: FileTimelineController,
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
exports.FileTimelineDirective.directive_name = 'grrFileTimeline';
