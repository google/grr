'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewController');
goog.provide('grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewDirective');
goog.require('grrUi.client.virtualFileSystem.events');
goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');

goog.scope(function() {

var REFRESH_FILE_EVENT =
    grrUi.client.virtualFileSystem.events.REFRESH_FILE_EVENT;

var ERROR_EVENT_NAME =
    grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.error_event_name;

var OPERATION_POLL_INTERVAL = 1000;


/**
 * Controller for FileDownloadViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewController = function(
    $rootScope, $scope, $interval, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {?string} */
  this.updateOperationId;

  /** @private {!angular.$q.Promise} */
  this.updateOperationInterval_;

  /** @private {boolean} */
  this.updateInProgress;

  /** @type {string} */
  this.downloadCommand;

  /** @type {Object} */
  this.fileDetails;

  this.scope_.$watchGroup(['controller.fileContext.clientId',
                           'controller.fileContext.selectedFilePath',
                           'controller.fileContext.selectedFileVersion'],
      this.onContextChange_.bind(this));

  this.scope_.$on('$destroy',
      this.stopMonitorUpdateOperation_.bind(this));
};

var FileDownloadViewController =
    grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewController;


/**
 * Handles changes to the clientId and filePath.
 *
 * @private
 */
FileDownloadViewController.prototype.onContextChange_ = function() {
  var clientId = this.fileContext['clientId'];
  var filePath = this.fileContext['selectedFilePath'];
  var fileVersion = this.fileContext['selectedFileVersion'];

  if (angular.isDefined(clientId) && angular.isDefined(filePath)) {

    var commandUrl = 'clients/' + clientId + '/vfs-download-command/' + filePath;
    this.grrApiService_.get(commandUrl).then(function(response) {
      this.downloadCommand = response.data['command'];
    }.bind(this));

    var detailsUrl = 'clients/' + clientId + '/vfs-details/' + filePath;
    var params = {};
    if (fileVersion) {
      params['timestamp'] = fileVersion;
    }
    this.grrApiService_.get(detailsUrl, params).then(function(response) {
      this.fileDetails = response.data['file'];
    }.bind(this));

  }
};

/**
 * Updates the current file.
 *
 * @export
 */
FileDownloadViewController.prototype.updateFile = function() {
  if (this.updateInProgress) {
    return;
  }

  var clientId = this.fileContext['clientId'];
  var selectedFilePath = this.fileContext['selectedFilePath'];
  var url = 'clients/' + clientId + '/vfs-update';
  var params = {
    file_path: selectedFilePath,
  };

  this.updateInProgress = true;
  this.grrApiService_.post(url, params).then(
      function success(response) {
        this.updateOperationId = response['data']['operation_id'];
        this.monitorUpdateOperation_();
      }.bind(this),
      function failure(response) {
        this.stopMonitorUpdateOperation_();
      }.bind(this));
};

/**
 * Periodically checks the update operation.
 *
 * @private
 */
FileDownloadViewController.prototype.monitorUpdateOperation_ = function() {
  this.updateOperationInterval_ = this.interval_(
      this.pollUpdateOperationState_.bind(this),
      OPERATION_POLL_INTERVAL);
};

/**
 * Polls the update operation state.
 *
 * @private
 */
FileDownloadViewController.prototype.pollUpdateOperationState_ = function() {
  var clientId = this.fileContext['clientId'];
  var url = 'clients/' + clientId + '/vfs-update/' + this.updateOperationId;

  this.grrApiService_.get(url).then(
    function success(response) {
      if (response['data']['state'] === 'FINISHED') {
        this.rootScope_.$broadcast(REFRESH_FILE_EVENT);
        this.stopMonitorUpdateOperation_();
      }
    }.bind(this),
    function failure(response) {
      this.stopMonitorUpdateOperation_();
    }.bind(this));
};

/**
 * Stops the peridoc operation state checks.
 *
 * @private
 */
FileDownloadViewController.prototype.stopMonitorUpdateOperation_ = function() {
  this.updateOperationId = null;
  this.updateInProgress = false;
  this.interval_.cancel(this.updateOperationInterval_);
};

/**
 * Downloades the file.
 *
 * @export
 */
FileDownloadViewController.prototype.downloadFile = function() {
  var clientId = this.fileContext['clientId'];
  var filePath = this.fileContext['selectedFilePath'];
  var fileVersion = this.fileContext['selectedFileVersion'];

  var url = 'clients/' + clientId + '/vfs-blob/' + filePath;
  var params = {};
  if (fileVersion) {
    params['timestamp'] = fileVersion;
  }
  this.grrApiService_.downloadFile(url, params).then(
      function success() {}.bind(this),
      function failure(response) {
        if (angular.isUndefined(response.status)) {
          this.rootScope_.$broadcast(
              ERROR_EVENT_NAME, {
                message: 'Couldn\'t download file.'
              });
        }
      }.bind(this)
  );
};


/**
 * FileDownloadViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    require: '^grrFileContext',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-download-view.html',
    controller: FileDownloadViewController,
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
grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewDirective.directive_name =
    'grrFileDownloadView';

});  // goog.scope
