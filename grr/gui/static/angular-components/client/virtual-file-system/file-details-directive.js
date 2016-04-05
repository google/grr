'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileDetailsDirective.FileDetailsController');
goog.provide('grrUi.client.virtualFileSystem.fileDetailsDirective.FileDetailsDirective');

goog.scope(function() {

/**
 * Controller for FileDetailsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileDetailsDirective.FileDetailsController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.selectedFileName;

  /** @type {Object} */
  this.fileDetails;

  /** @type {string} */
  this.fileVersionUrl;

  /** @type {number} */
  this.fileVersion;

  /** @type {boolean} */
  this.fileIsDirectory;

  /** @type {boolean} */
  this.showDefaultTab;

  /** @type {string} */
  this.downloadAff4Path;

  this.scope_.$watchGroup(['clientId', 'selectedFilePath'],
      this.onDirectiveArgumentsChange_.bind(this));
};

var FileDetailsController =
    grrUi.client.virtualFileSystem.fileDetailsDirective.FileDetailsController;


/**
 * Is triggered whenever the client id or the selected folder path changes.
 *
 * @private
 */
FileDetailsController.prototype.onDirectiveArgumentsChange_ = function(){
  var clientId = this.scope_['clientId'];
  var selectedFilePath = this.scope_['selectedFilePath'];

  if (angular.isDefined(clientId) && angular.isDefined(selectedFilePath)) {
    var components = selectedFilePath.split('/');
    this.selectedFileName = components[components.length - 1];

    this.fileVersionUrl = 'clients/' + clientId + '/vfs-version-times/' + selectedFilePath;
    this.showDefaultTab = true;
    this.fetchFileDetails_();
  }
};

/**
 * Fetches the file details specified by clientId, the file path and the selected version.
 *
 * @private
 */
FileDetailsController.prototype.fetchFileDetails_ = function() {
  var clientId = this.scope_['clientId'];
  var selectedFilePath = this.scope_['selectedFilePath'];
  var url = 'clients/' + clientId + '/vfs-details/' + selectedFilePath;

  this.grrApiService_.get(url).then(function(response) {
    this.fileDetails = response.data['file'];
    this.fileVersion = this.fileDetails['age'];
    this.fileIsDirectory = this.fileDetails['value']['is_directory']['value'];
    this.downloadAff4Path = 'aff4:/' + clientId + '/' + selectedFilePath;
  }.bind(this));
};

/**
 * Is triggered whenever an breadcrumb item was selected.
 *
 * @param {string} path
 * @export
 */
FileDetailsController.prototype.onBreadCrumbSelected = function(path) {
  this.scope_['selectedFolderPath'] = path;
  this.scope_['selectedFilePath'] = path;
};

/**
 * FileDetailsDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileDetailsDirective.FileDetailsDirective = function() {
  return {
    restrict: 'E',
    scope: {
      clientId: '=',
      selectedFilePath: '=',
      selectedFolderPath: '='
    },
    templateUrl: '/static/angular-components/client/virtual-file-system/file-details.html',
    controller: FileDetailsController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileDetailsDirective.FileDetailsDirective.directive_name =
    'grrFileDetails';

});  // goog.scope
