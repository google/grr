'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewController');
goog.provide('grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewDirective');


goog.scope(function() {


/**
 * Controller for FileDownloadViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileDownloadViewDirective.FileDownloadViewController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.downloadCommand;

  /** @type {Object} */
  this.fileDetails;

  this.scope_.$watchGroup(['controller.fileContext.clientId',
                           'controller.fileContext.selectedFilePath',
                           'controller.fileContext.selectedFileVersion'],
      this.onContextChange_.bind(this));
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
  // TODO(user): Add version.

  if (angular.isDefined(clientId) && angular.isDefined(filePath)) {

    var commandUrl = 'clients/' + clientId + '/vfs-download-command/' + filePath;
    this.grrApiService_.get(commandUrl).then(function(response) {
      this.downloadCommand = response.data['command'];
    }.bind(this));

    var detailsUrl = 'clients/' + clientId + '/vfs-details/' + filePath;
    this.grrApiService_.get(detailsUrl).then(function(response) {
      this.fileDetails = response.data['file'];
    }.bind(this));

  }
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
