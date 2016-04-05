'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileStatsViewDirective.FileStatsViewController');
goog.provide('grrUi.client.virtualFileSystem.fileStatsViewDirective.FileStatsViewDirective');


goog.scope(function() {


/**
 * Controller for FileStatsViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileStatsViewDirective.FileStatsViewController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Object} */
  this.details;

  this.scope_.$watchGroup(['clientId', 'filePath', 'fileVersion'],
      this.onDirectiveArgumentsChange_.bind(this));
};

var FileStatsViewController =
    grrUi.client.virtualFileSystem.fileStatsViewDirective.FileStatsViewController;


/**
 * Handles changes to the clientId and filePath.
 *
 * @private
 */
FileStatsViewController.prototype.onDirectiveArgumentsChange_ = function() {
  var clientId = this.scope_['clientId'];
  var filePath = this.scope_['filePath'];
  var fileVersion = this.scope_['fileVersion'];

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
grrUi.client.virtualFileSystem.fileStatsViewDirective.FileStatsViewDirective = function() {
  return {
    restrict: 'E',
    scope: {
      clientId: '=',
      filePath: '=',
      fileVersion: '='
    },
    templateUrl: '/static/angular-components/client/virtual-file-system/file-stats-view.html',
    controller: FileStatsViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileStatsViewDirective.FileStatsViewDirective.directive_name =
    'grrFileStatsView';

});  // goog.scope
