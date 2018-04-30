'use strict';

goog.module('grrUi.client.virtualFileSystem.fileStatsViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for FileStatsViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const FileStatsViewController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  /** @type {Object} */
  this.details;

  this.scope_.$watchGroup(['controller.fileContext.clientId',
                           'controller.fileContext.selectedFilePath',
                           'controller.fileContext.selectedFileVersion'],
      this.onContextChange_.bind(this));
};



/**
 * Handles changes to the clientId and filePath.
 *
 * @private
 */
FileStatsViewController.prototype.onContextChange_ = function() {
  var clientId = this.fileContext['clientId'];
  var filePath = this.fileContext['selectedFilePath'];
  var fileVersion = this.fileContext['selectedFileVersion'];

  if (angular.isDefined(clientId) && angular.isDefined(filePath)) {
    var fileDetailsUrl = 'clients/' + clientId + '/vfs-details/' + filePath;
    var params = {};
    if (fileVersion) {
      params['timestamp'] = fileVersion;
    }

    this.grrApiService_.get(fileDetailsUrl, params).then(function(response) {
      this.details = response.data['file']['value']['details'];
    }.bind(this));
  }
};


/**
 * FileStatsViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.FileStatsViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    require: '^grrFileContext',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-stats-view.html',
    controller: FileStatsViewController,
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
exports.FileStatsViewDirective.directive_name = 'grrFileStatsView';
