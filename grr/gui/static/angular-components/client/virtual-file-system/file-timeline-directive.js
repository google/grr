'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileTimelineDirective.FileTimelineController');
goog.provide('grrUi.client.virtualFileSystem.fileTimelineDirective.FileTimelineDirective');
goog.require('grrUi.client.virtualFileSystem.events');

goog.scope(function() {

var REFRESH_FOLDER_EVENT =
    grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT;
var REFRESH_FILE_EVENT =
    grrUi.client.virtualFileSystem.events.REFRESH_FILE_EVENT;

/**
 * Controller for FileTimelineDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileTimelineDirective.FileTimelineController = function(
    $scope, $interval, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  /** @type {Array} */
  this.timelineItems;

  /** @type {boolean} */
  this.inProgress;

  /**
   * This variable is set to a function by the infinite-table-directive
   * and can be used to force data reload from the server.
   *
   * @export {function()}
   */
  this.triggerUpdate;

  this.scope_.$on(REFRESH_FOLDER_EVENT,
      this.refreshTimeline_.bind(this));
  this.scope_.$on(REFRESH_FILE_EVENT,
      this.refreshTimeline_.bind(this));

  this.scope_.$watchGroup(['controller.fileContext.clientId',
                           'controller.fileContext.selectedFolderPath'],
      this.refreshTimeline_.bind(this));
};

var FileTimelineController =
    grrUi.client.virtualFileSystem.fileTimelineDirective.FileTimelineController;


/**
 * Refreshes the current timeline view.
 *
 * @private
 */
FileTimelineController.prototype.refreshTimeline_ = function() {
  var clientId = this.fileContext['clientId'];
  var selectedFolderPath = this.fileContext['selectedFolderPath'];

  this.inProgress = true;

  var url = 'clients/' + clientId + '/vfs-timeline/' + selectedFolderPath;
  this.grrApiService_.get(url).then(function success(response) {
    this.timelineItems = response.data['items'];

    if (this.triggerUpdate) {
      this.triggerUpdate();
    }

    this.inProgress = false;
  }.bind(this), function failed() {
    this.inProgress = false;
  }.bind(this));
};

/**
 * Selects the file causing the timeline event.
 *
 * @param {Object} timelineItem
 * @export
 */
FileTimelineController.prototype.selectFile = function(timelineItem) {
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
grrUi.client.virtualFileSystem.fileTimelineDirective.FileTimelineDirective = function() {
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
grrUi.client.virtualFileSystem.fileTimelineDirective.FileTimelineDirective.directive_name =
    'grrFileTimeline';

});  // goog.scope
