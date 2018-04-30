'use strict';

goog.module('grrUi.client.virtualFileSystem.fileDetailsDirective');
goog.module.declareLegacyNamespace();

const {REFRESH_FILE_EVENT} = goog.require('grrUi.client.virtualFileSystem.events');
const {VersionDropdownDirective} = goog.require('grrUi.core.versionDropdownDirective');



var REFRESH_VERSIONS_EVENT = VersionDropdownDirective.REFRESH_VERSIONS_EVENT;

/**
 * Controller for FileDetailsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const FileDetailsController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.shownFileName;

  /** @type {string} */
  this.fileVersionUrl;

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  /** @type {boolean} */
  this.fileIsDirectory;

  /** @type {Object} */
  this.downloadQueryParams;

  /** @type {string} */
  this.currentTab = 'stats';

  this.scope_.$on(REFRESH_FILE_EVENT,
      this.refreshFile_.bind(this));

  this.scope_.$watch('currentTab', this.onDirectiveTabChange_.bind(this));
  this.scope_.$watch('controller.currentTab', this.onControllerTabChange_.bind(this));

  this.scope_.$watchGroup(['controller.fileContext.clientId',
                           'controller.fileContext.selectedFilePath',
                           'controller.fileContext.selectedFileVersion'],
      this.onContextChange_.bind(this));
};



/**
 * Handles currentTab scope attribute changes.
 *
 * @param {string} newValue
 * @private
 */
FileDetailsController.prototype.onDirectiveTabChange_ = function(newValue) {
  if (angular.isString(newValue)) {
    this.currentTab = newValue;
  }
};

/**
 * Handles controller's currentTab attribute changes.
 *
 * @param {string} newValue
 * @param {string} oldValue
 * @private
 */
FileDetailsController.prototype.onControllerTabChange_ = function(newValue, oldValue) {
  if (newValue !== oldValue) {
    this.scope_['currentTab'] = newValue;
  }
};


/**
 * Is triggered whenever the file context changes.
 *
 * @private
 */
FileDetailsController.prototype.onContextChange_ = function(){
  var clientId = this.fileContext['clientId'];
  var selectedFilePath = this.fileContext['selectedFilePath'];

  if (angular.isDefined(clientId) && angular.isDefined(selectedFilePath)) {
    this.fetchFileDetails_();
  }
};

/**
 * Fetches the file details specified by clientId, the file path and the selected version.
 *
 * @private
 */
FileDetailsController.prototype.fetchFileDetails_ = function() {
  var clientId = this.fileContext['clientId'];
  var selectedFilePath = this.fileContext['selectedFilePath'];
  var fileVersion = this.fileContext['selectedFileVersion'];

  var url = 'clients/' + clientId + '/vfs-details/' + selectedFilePath;
  var params = {};
  if (fileVersion) {
    params['timestamp'] = fileVersion;
  }

  this.grrApiService_.get(url, params).then(
      this.onFileDetailsFetched_.bind(this));
};

/**
 * Called when the file details were fetched.
 *
 * @param {Object} response
 * @private
 */
FileDetailsController.prototype.onFileDetailsFetched_ = function(response) {
  var clientId = this.fileContext['clientId'];
  var selectedFilePath = this.fileContext['selectedFilePath'];
  var fileVersion = this.fileContext['selectedFileVersion'];
  var fileDetails = response.data['file'];

  this.fileVersionUrl = 'clients/' + clientId + '/vfs-version-times/' + selectedFilePath;
  this.fileIsDirectory = fileDetails['value']['is_directory']['value'];

  this.downloadQueryParams = {
    clientId: clientId,
    aff4_path: 'aff4:/' + clientId + '/' + selectedFilePath,
  };
  if (fileVersion) {
    this.downloadQueryParams['age'] = fileVersion;
  }

  var components = fileDetails['value']['path']['value'].split('/');
  this.selectedFileName = components[components.length - 1];
};

/**
 * Refreshes the file by fetching the file details with the latest version.
 *
 * @private
 */
FileDetailsController.prototype.refreshFile_ = function() {
  this.fileContext['selectedFileVersion'] = undefined;
  this.scope_.$broadcast(REFRESH_VERSIONS_EVENT, {});
  this.fetchFileDetails_();
};

/**
 * Checks whether the path in the file details and the currently selected file path match.
 *
 * @param {Object} fileDetails The details of the currently fetched file.
 * @return {boolean} True if the file details target the current selection, false otherwise.
 * @private
 */
FileDetailsController.prototype.targetsCurrentSelection_ = function(fileDetails) {
  var selectedFilePath = this.fileContext['selectedFilePath'];
  return fileDetails['value']['path']['value'] === selectedFilePath;
};

/**
 * FileDetailsDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.FileDetailsDirective = function() {
  return {
    restrict: 'E',
    scope: {
      currentTab: '='
    },
    require: '^grrFileContext',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-details.html',
    controller: FileDetailsController,
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
exports.FileDetailsDirective.directive_name = 'grrFileDetails';
